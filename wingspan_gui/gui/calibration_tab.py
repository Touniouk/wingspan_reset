"""Calibration tab: capture a live screenshot and click/drag directly on it to
set bird/tray/EOR regions and button points, instead of hand-editing fractions."""

import copy
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

from PIL import ImageTk

from wingspan_gui import platform_io
from wingspan_gui.calibration_math import (
    canvas_point_to_fraction,
    canvas_rect_to_fraction,
    fraction_point_to_canvas,
    fraction_rect_to_canvas,
)
from wingspan_gui.config import DEFAULT_CONFIG_PATH, SCREENSHOT_DIR
from wingspan_gui.ocr import crop_region_and_check_ocr

# Fixed size of the visible canvas viewport - the captured screenshot renders at
# native resolution (for calibration precision) and may be larger than this, in
# which case the scrollbars let you pan around it instead of it being shrunk to fit.
VIEWPORT_W = 1000
VIEWPORT_H = 650

REGION_KINDS = ('starting_bird', 'tray_bird', 'eor')
KIND_LABELS = {'starting_bird': 'bird', 'tray_bird': 'tray', 'eor': 'eor', 'button': 'button'}
KIND_TO_CFG_ATTR = {'starting_bird': 'starting_birds', 'tray_bird': 'tray_birds', 'eor': 'eor_goals'}


class CalibrationTab(ttk.Frame):
    def __init__(self, parent, cfg, logger):
        super().__init__(parent)
        self.cfg = cfg
        self.logger = logger

        self.full_img = None
        self.tk_image = None
        self.display_scale = 1.0
        self.img_w = 0
        self.img_h = 0

        self.selected_item: tuple[str, str] | None = None
        self._drag_start = None
        self._drag_rect_id = None

        self._load_working_copies()
        self._build_ui()

    # --- working-copy management ---------------------------------------------

    def _load_working_copies(self):
        """Deep-copy the editable pieces of cfg so drags don't touch the shared
        config until an explicit Save."""
        self.working_starting_birds = copy.deepcopy(self.cfg.starting_birds)
        self.working_tray_birds = copy.deepcopy(self.cfg.tray_birds)
        self.working_eor_goals = copy.deepcopy(self.cfg.eor_goals)
        self.working_buttons = copy.deepcopy(self.cfg.buttons)

    def _working_list_for_kind(self, kind: str):
        return getattr(self, f"working_{KIND_TO_CFG_ATTR.get(kind, '')}", None) if kind in KIND_TO_CFG_ATTR else None

    def _find_working_region(self, kind: str, name: str):
        for region in self._working_list_for_kind(kind) or []:
            if region.name == name:
                return region
        return None

    # --- UI construction -------------------------------------------------------

    def _build_ui(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=8, pady=8)

        left = ttk.Frame(container)
        left.pack(side="left", fill="y", padx=(0, 8))

        ttk.Button(left, text="Capture Screenshot", command=self._start_capture_countdown).pack(fill="x", pady=2)
        self.countdown_label = ttk.Label(left, text="")
        self.countdown_label.pack(fill="x")

        ttk.Label(left, text="Select an item to edit:").pack(anchor="w", pady=(10, 0))
        self.item_listbox = tk.Listbox(left, width=28, height=16, exportselection=False)
        self.item_listbox.pack(fill="both", pady=2)
        self.item_listbox.bind("<<ListboxSelect>>", self._on_item_selected)
        self._populate_item_list()

        self.instruction_label = ttk.Label(left, text="Select an item above, then\ninteract with the image.",
                                            wraplength=220, justify="left")
        self.instruction_label.pack(fill="x", pady=8)

        ttk.Button(left, text="Test OCR on current regions", command=self._test_ocr).pack(fill="x", pady=(10, 2))
        self.ocr_results = tk.Text(left, width=28, height=10, wrap="word")
        self.ocr_results.pack(fill="both", pady=2)

        save_bar = ttk.Frame(left)
        save_bar.pack(fill="x", pady=(10, 2))
        ttk.Button(save_bar, text="Save to Config", command=self._save).pack(side="left", padx=2)
        ttk.Button(save_bar, text="Revert", command=self._revert).pack(side="left", padx=2)

        right = ttk.Frame(container)
        right.pack(side="left", fill="both", expand=True)
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(right, width=VIEWPORT_W, height=VIEWPORT_H, bg="#222222",
                                 highlightthickness=1, highlightbackground="#444444")
        v_scroll = ttk.Scrollbar(right, orient="vertical", command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(right, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.canvas.configure(scrollregion=(0, 0, VIEWPORT_W, VIEWPORT_H))
        self.canvas.create_text(VIEWPORT_W // 2, VIEWPORT_H // 2,
                                 text="Click 'Capture Screenshot' to begin",
                                 fill="#999999", tags="placeholder")

        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

    def _populate_item_list(self):
        self.item_listbox.delete(0, tk.END)
        self._item_index = []  # parallel list of (kind, name) matching listbox rows

        for region in self.working_starting_birds:
            self.item_listbox.insert(tk.END, f"[bird] {region.name}")
            self._item_index.append(('starting_bird', region.name))
        for region in self.working_tray_birds:
            self.item_listbox.insert(tk.END, f"[tray] {region.name}")
            self._item_index.append(('tray_bird', region.name))
        for region in self.working_eor_goals:
            self.item_listbox.insert(tk.END, f"[eor] {region.name}")
            self._item_index.append(('eor', region.name))
        for name in self.working_buttons:
            self.item_listbox.insert(tk.END, f"[button] {name}")
            self._item_index.append(('button', name))

    # --- screenshot capture -------------------------------------------------------

    def _start_capture_countdown(self, seconds_left: int = 3):
        if seconds_left > 0:
            self.countdown_label.config(text=f"Capturing in {seconds_left}... (focus the Wingspan window)")
            self.after(1000, lambda: self._start_capture_countdown(seconds_left - 1))
        else:
            self.countdown_label.config(text="")
            self._capture_screenshot()

    def _capture_screenshot(self):
        w = self.cfg.window
        self.full_img = platform_io.take_screenshot(w.x_offset, w.y_offset, w.width, w.height)
        self.img_w, self.img_h = self.full_img.size
        # Render at native resolution for calibration precision; the fixed-size
        # viewport + scrollbars handle images larger than what's visible at once.
        self.display_scale = 1.0
        self.tk_image = ImageTk.PhotoImage(self.full_img)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw", tags="base_image")
        self.canvas.configure(scrollregion=(0, 0, self.img_w, self.img_h))
        self._redraw_overlays()

    # --- overlay drawing -------------------------------------------------------

    def _redraw_overlays(self):
        if self.full_img is None:
            return
        self.canvas.delete("overlay")

        all_regions = [('starting_bird', r) for r in self.working_starting_birds]
        all_regions += [('tray_bird', r) for r in self.working_tray_birds]
        all_regions += [('eor', r) for r in self.working_eor_goals]

        for kind, region in all_regions:
            x0, y0, x1, y1 = fraction_rect_to_canvas(region.x, region.y, region.w, region.h,
                                                       self.display_scale, self.img_w, self.img_h)
            is_selected = self.selected_item == (kind, region.name)
            self.canvas.create_rectangle(x0, y0, x1, y1, outline=self._rgb(region.color),
                                          width=3 if is_selected else 2, tags="overlay")

        for name, button in self.working_buttons.items():
            cx, cy = fraction_point_to_canvas(button.x, button.y, self.display_scale, self.img_w, self.img_h)
            is_selected = self.selected_item == ('button', name)
            size = 8 if is_selected else 5
            color = "#ffff00" if is_selected else "#ffffff"
            self.canvas.create_line(cx - size, cy, cx + size, cy, fill=color, width=2, tags="overlay")
            self.canvas.create_line(cx, cy - size, cx, cy + size, fill=color, width=2, tags="overlay")

    @staticmethod
    def _rgb(color) -> str:
        r, g, b = color
        return f"#{r:02x}{g:02x}{b:02x}"

    # --- selection -------------------------------------------------------------

    def _on_item_selected(self, event):
        selection = self.item_listbox.curselection()
        if not selection:
            return
        self.selected_item = self._item_index[selection[0]]
        kind, name = self.selected_item
        if kind == 'button':
            self.instruction_label.config(text=f"[button] {name}\nClick on the image to set this point.")
        else:
            self.instruction_label.config(text=f"[{KIND_LABELS[kind]}] {name}\nClick and drag on the image to redraw this region.")
        self._redraw_overlays()

    # --- canvas interaction -------------------------------------------------------

    def _on_canvas_press(self, event):
        if self.full_img is None or self.selected_item is None:
            return
        kind, name = self.selected_item
        # Mouse events report coordinates relative to the visible viewport, not
        # the underlying scrollable canvas - convert to canvas space so drags
        # land in the right place even when scrolled.
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        if kind == 'button':
            xr, yr = canvas_point_to_fraction(x, y, self.display_scale, self.img_w, self.img_h)
            self.working_buttons[name].x = xr
            self.working_buttons[name].y = yr
            self._redraw_overlays()
            return

        self._drag_start = (x, y)
        self._drag_rect_id = self.canvas.create_rectangle(
            x, y, x, y, outline="#ffff00", width=2, dash=(4, 2), tags="drag_temp"
        )

    def _on_canvas_drag(self, event):
        if self._drag_rect_id is None or self._drag_start is None:
            return
        x0, y0 = self._drag_start
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self._drag_rect_id, x0, y0, x, y)

    def _on_canvas_release(self, event):
        if self._drag_rect_id is None or self._drag_start is None or self.selected_item is None:
            return
        kind, name = self.selected_item
        x0, y0 = self._drag_start
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        fraction = canvas_rect_to_fraction(x0, y0, x, y, self.display_scale, self.img_w, self.img_h)
        region = self._find_working_region(kind, name)
        if region is not None and fraction['w'] > 0 and fraction['h'] > 0:
            region.x, region.y, region.w, region.h = fraction['x'], fraction['y'], fraction['w'], fraction['h']

        self.canvas.delete("drag_temp")
        self._drag_rect_id = None
        self._drag_start = None
        self._redraw_overlays()

    # --- OCR test / save / revert -------------------------------------------------------

    def _test_ocr(self):
        if self.full_img is None:
            messagebox.showwarning("No screenshot", "Capture a screenshot first.")
            return

        self.ocr_results.delete("1.0", tk.END)
        Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime('%Y%m%d_%H%M%S')

        all_regions = self.working_starting_birds + self.working_tray_birds + self.working_eor_goals
        for region in all_regions:
            result = crop_region_and_check_ocr(self.full_img, timestamp, region, self.logger)
            self.ocr_results.insert(tk.END, f"{region.name}: {result}\n")

    def _save(self):
        self.cfg.starting_birds = self.working_starting_birds
        self.cfg.tray_birds = self.working_tray_birds
        self.cfg.eor_goals = self.working_eor_goals
        self.cfg.buttons = self.working_buttons
        self.cfg.save(DEFAULT_CONFIG_PATH)
        messagebox.showinfo("Saved", f"Calibration saved to {DEFAULT_CONFIG_PATH}")

    def _revert(self):
        self._load_working_copies()
        self.selected_item = None
        self._populate_item_list()
        self._redraw_overlays()
