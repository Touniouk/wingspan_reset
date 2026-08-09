"""Tk root application: wires Params/Run tabs, the worker thread, and the
global stop hotkey together."""

import threading
import tkinter as tk
from tkinter import ttk

from logger import Logger  # type: ignore

from wingspan_gui.automation import reload_until_threshold_met
from wingspan_gui.config import AppConfig, DEFAULT_LOG_PATH
from wingspan_gui.gui.calibration_tab import CalibrationTab
from wingspan_gui.gui.params_tab import ParamsTab
from wingspan_gui.gui.run_tab import RunTab
from wingspan_gui.logging_bridge import TkLogBridge
from wingspan_gui.platform_io import GlobalHotkeyListener

WORKER_POLL_MS = 300


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Wingspan Automation")
        root.geometry("1100x750")

        self.cfg = AppConfig.load()
        self.stop_event = threading.Event()
        self.worker_thread: threading.Thread | None = None

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        self.run_tab = RunTab(notebook, self.cfg, on_start=self.on_start, on_stop=self.on_stop)
        notebook.add(self.run_tab, text="Run")

        self.log_bridge = TkLogBridge(self.run_tab.log_text, root)
        self.log_bridge.start_polling()

        self.logger = Logger(level=Logger.SILLY, log_file=str(DEFAULT_LOG_PATH),
                              enable_color_in_file=True, on_log=self.log_bridge.on_log)

        self.params_tab = ParamsTab(notebook, self.cfg, on_save=self._on_params_saved)
        notebook.add(self.params_tab, text="Params")

        self.calibration_tab = CalibrationTab(notebook, self.cfg, self.logger)
        notebook.add(self.calibration_tab, text="Calibration")

        self.hotkey = GlobalHotkeyListener(self.stop_event)
        self.hotkey.start()

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._poll_worker()

    def on_start(self, automa: bool, continue_on_match: bool) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            return
        self.stop_event.clear()
        self.worker_thread = threading.Thread(
            target=reload_until_threshold_met,
            args=(self.cfg, self.stop_event, self.logger),
            kwargs={'continue_on_match': continue_on_match, 'automa': automa},
            daemon=True,
        )
        self.worker_thread.start()
        self.run_tab.set_running(True)

    def on_stop(self) -> None:
        self.stop_event.set()

    def _on_params_saved(self) -> None:
        # cfg is a single shared object mutated in place, so Run tab checkboxes
        # and the worker thread already see saved changes - nothing else needed.
        pass

    def _poll_worker(self) -> None:
        if self.worker_thread and not self.worker_thread.is_alive():
            self.run_tab.set_running(False)
            self.worker_thread = None
        self.root.after(WORKER_POLL_MS, self._poll_worker)

    def on_close(self) -> None:
        self.stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2)
        self.hotkey.stop()
        self.root.destroy()
