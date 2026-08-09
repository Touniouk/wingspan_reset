"""Run tab: Start/Stop controls, run options, and a live scrolling log."""

import tkinter as tk
from tkinter import ttk


class RunTab(ttk.Frame):
    def __init__(self, parent, cfg, on_start, on_stop):
        super().__init__(parent)
        self.cfg = cfg
        self.on_start = on_start
        self.on_stop = on_stop

        self.automa_var = tk.BooleanVar(value=cfg.run_options.automa)
        self.continue_on_match_var = tk.BooleanVar(value=cfg.run_options.continue_on_match)

        self._build_ui()

    def _build_ui(self):
        options = ttk.Frame(self)
        options.pack(fill="x", padx=8, pady=6)
        ttk.Checkbutton(options, text="Automa mode", variable=self.automa_var).pack(side="left", padx=4)
        ttk.Checkbutton(
            options,
            text="Keep reloading after a match is found (uncheck to stop + play alert)",
            variable=self.continue_on_match_var,
        ).pack(side="left", padx=4)

        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=8, pady=6)
        self.start_button = ttk.Button(controls, text="Start", command=self._handle_start)
        self.start_button.pack(side="left", padx=4)
        self.stop_button = ttk.Button(controls, text="Stop", command=self._handle_stop, state="disabled")
        self.stop_button.pack(side="left", padx=4)
        self.status_label = ttk.Label(controls, text="Idle")
        self.status_label.pack(side="left", padx=12)
        ttk.Label(controls, text="(Esc also stops immediately, from anywhere)").pack(side="left", padx=4)

        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True, padx=8, pady=6)

        self.log_text = tk.Text(log_frame, height=20, wrap="word", bg="#111111", fg="#e5e5e5",
                                 insertbackground="#e5e5e5")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _handle_start(self):
        self.cfg.run_options.automa = self.automa_var.get()
        self.cfg.run_options.continue_on_match = self.continue_on_match_var.get()
        self.on_start(automa=self.cfg.run_options.automa,
                      continue_on_match=self.cfg.run_options.continue_on_match)

    def _handle_stop(self):
        self.on_stop()

    def set_running(self, running: bool):
        self.start_button.config(state="disabled" if running else "normal")
        self.stop_button.config(state="normal" if running else "disabled")
        self.status_label.config(text="Running..." if running else "Idle")
