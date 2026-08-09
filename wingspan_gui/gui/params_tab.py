"""Params tab: edit window geometry, scoring, bird points, and tunables."""

import tkinter as tk
from tkinter import ttk, messagebox

from wingspan_gui.config import AppConfig, DEFAULT_CONFIG_PATH


class ParamsTab(ttk.Frame):
    def __init__(self, parent, cfg: AppConfig, on_save=None):
        super().__init__(parent)
        self.cfg = cfg
        self.on_save = on_save
        self._bird_row_widgets: list[tuple[tk.StringVar, tk.IntVar, ttk.Frame]] = []

        self._build_scrollable_container()
        self._build_window_section()
        self._build_scoring_section()
        self._build_bird_points_section()
        self._build_tunables_section()
        self._build_alert_sound_section()
        self._build_save_bar()

        self._load_from_cfg()

    # --- layout scaffolding -------------------------------------------------

    def _build_scrollable_container(self):
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.body = ttk.Frame(canvas)

        self.body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _labeled_entry(self, parent, label, width=10):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, width=22, anchor="w").pack(side="left")
        var = tk.StringVar()
        ttk.Entry(row, textvariable=var, width=width).pack(side="left")
        return var

    # --- sections -------------------------------------------------------------

    def _build_window_section(self):
        frame = ttk.LabelFrame(self.body, text="Window Geometry")
        frame.pack(fill="x", padx=8, pady=6)
        self.window_x_offset = self._labeled_entry(frame, "X offset")
        self.window_y_offset = self._labeled_entry(frame, "Y offset")
        self.window_width = self._labeled_entry(frame, "Width")
        self.window_height = self._labeled_entry(frame, "Height")
        self.window_dead_height = self._labeled_entry(frame, "Dead height")

    def _build_scoring_section(self):
        frame = ttk.LabelFrame(self.body, text="Scoring")
        frame.pack(fill="x", padx=8, pady=6)
        self.no_goal_points = self._labeled_entry(frame, "NO GOAL points")
        self.point_threshold = self._labeled_entry(frame, "Point threshold")

    def _build_bird_points_section(self):
        frame = ttk.LabelFrame(self.body, text="Bird Points")
        frame.pack(fill="x", padx=8, pady=6)

        header = ttk.Frame(frame)
        header.pack(fill="x")
        ttk.Label(header, text="Bird common name", width=28, anchor="w").pack(side="left")
        ttk.Label(header, text="Points", width=8, anchor="w").pack(side="left")

        self.bird_rows_container = ttk.Frame(frame)
        self.bird_rows_container.pack(fill="x")

        ttk.Button(frame, text="+ Add bird", command=lambda: self._add_bird_row()).pack(anchor="w", pady=4)

    def _build_tunables_section(self):
        frame = ttk.LabelFrame(self.body, text="Tunables")
        frame.pack(fill="x", padx=8, pady=6)
        self.screenshots_to_keep = self._labeled_entry(frame, "Screenshots to keep")
        self.bird_match_minimum_ratio = self._labeled_entry(frame, "Bird match min ratio")
        self.window_ready_delay = self._labeled_entry(frame, "Window ready delay (s)")
        self.grid_spacing_px = self._labeled_entry(frame, "Grid spacing (px)")

    def _build_alert_sound_section(self):
        frame = ttk.LabelFrame(self.body, text="Alert Sound")
        frame.pack(fill="x", padx=8, pady=6)
        self.alert_sound_macos = self._labeled_entry(frame, "macOS sound path", width=40)
        self.alert_sound_windows = self._labeled_entry(frame, "Windows sound path (optional)", width=40)

    def _build_save_bar(self):
        bar = ttk.Frame(self.body)
        bar.pack(fill="x", padx=8, pady=10)
        ttk.Button(bar, text="Save", command=self.save).pack(side="left", padx=4)
        ttk.Button(bar, text="Revert", command=self.revert).pack(side="left", padx=4)

    # --- bird row management -------------------------------------------------

    def _add_bird_row(self, name: str = "", points: int = 1):
        row = ttk.Frame(self.bird_rows_container)
        row.pack(fill="x", pady=1)

        name_var = tk.StringVar(value=name)
        points_var = tk.IntVar(value=points)

        ttk.Entry(row, textvariable=name_var, width=28).pack(side="left")
        ttk.Spinbox(row, textvariable=points_var, from_=0, to=99, width=6).pack(side="left")
        remove_btn = ttk.Button(row, text="Remove", command=lambda: self._remove_bird_row(row))
        remove_btn.pack(side="left", padx=4)

        self._bird_row_widgets.append((name_var, points_var, row))

    def _remove_bird_row(self, row_to_remove):
        self._bird_row_widgets = [
            (n, p, r) for (n, p, r) in self._bird_row_widgets if r is not row_to_remove
        ]
        row_to_remove.destroy()

    def _clear_bird_rows(self):
        for _, _, row in self._bird_row_widgets:
            row.destroy()
        self._bird_row_widgets = []

    # --- load/save -------------------------------------------------------------

    def _load_from_cfg(self):
        w = self.cfg.window
        self.window_x_offset.set(str(w.x_offset))
        self.window_y_offset.set(str(w.y_offset))
        self.window_width.set(str(w.width))
        self.window_height.set(str(w.height))
        self.window_dead_height.set(str(w.dead_height))

        self.no_goal_points.set(str(self.cfg.no_goal_points))
        self.point_threshold.set(str(self.cfg.point_threshold))

        self._clear_bird_rows()
        for name, points in self.cfg.bird_points.items():
            self._add_bird_row(name, points)

        t = self.cfg.tunables
        self.screenshots_to_keep.set(str(t.screenshots_to_keep))
        self.bird_match_minimum_ratio.set(str(t.bird_match_minimum_ratio))
        self.window_ready_delay.set(str(t.window_ready_delay))
        self.grid_spacing_px.set(str(t.grid_spacing_px))

        self.alert_sound_macos.set(self.cfg.alert_sound_macos or "")
        self.alert_sound_windows.set(self.cfg.alert_sound_windows or "")

    def save(self):
        try:
            self.cfg.window.x_offset = int(self.window_x_offset.get())
            self.cfg.window.y_offset = int(self.window_y_offset.get())
            self.cfg.window.width = int(self.window_width.get())
            self.cfg.window.height = int(self.window_height.get())
            self.cfg.window.dead_height = int(self.window_dead_height.get())

            self.cfg.no_goal_points = int(self.no_goal_points.get())
            self.cfg.point_threshold = int(self.point_threshold.get())

            new_bird_points = {}
            for name_var, points_var, _ in self._bird_row_widgets:
                name = name_var.get().strip()
                if name:
                    new_bird_points[name] = int(points_var.get())
            self.cfg.bird_points = new_bird_points

            self.cfg.tunables.screenshots_to_keep = int(self.screenshots_to_keep.get())
            self.cfg.tunables.bird_match_minimum_ratio = float(self.bird_match_minimum_ratio.get())
            self.cfg.tunables.window_ready_delay = float(self.window_ready_delay.get())
            self.cfg.tunables.grid_spacing_px = int(self.grid_spacing_px.get())

            self.cfg.alert_sound_macos = self.alert_sound_macos.get().strip()
            windows_path = self.alert_sound_windows.get().strip()
            self.cfg.alert_sound_windows = windows_path or None
        except ValueError as e:
            messagebox.showerror("Invalid value", f"Couldn't save: {e}")
            return

        self.cfg.save(DEFAULT_CONFIG_PATH)
        if self.on_save:
            self.on_save()
        messagebox.showinfo("Saved", f"Config saved to {DEFAULT_CONFIG_PATH}")

    def revert(self):
        fresh = AppConfig.load(DEFAULT_CONFIG_PATH)
        # Mutate cfg in place so other tabs holding a reference to the same
        # object (e.g. RunTab) see the reverted values too.
        self.cfg.window = fresh.window
        self.cfg.buttons = fresh.buttons
        self.cfg.starting_birds = fresh.starting_birds
        self.cfg.tray_birds = fresh.tray_birds
        self.cfg.eor_goals = fresh.eor_goals
        self.cfg.bird_points = fresh.bird_points
        self.cfg.no_goal_points = fresh.no_goal_points
        self.cfg.point_threshold = fresh.point_threshold
        self.cfg.tunables = fresh.tunables
        self.cfg.alert_sound_macos = fresh.alert_sound_macos
        self.cfg.alert_sound_windows = fresh.alert_sound_windows
        self.cfg.run_options = fresh.run_options
        self._load_from_cfg()
