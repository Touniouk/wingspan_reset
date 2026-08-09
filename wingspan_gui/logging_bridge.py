"""Thread-safe bridge from Logger's on_log callback into a Tkinter Text widget.

The automation loop runs on a worker thread, but Tkinter widgets may only be
touched from the main thread. The worker thread enqueues log lines; the Tk
mainloop drains the queue on a timer via root.after().
"""

import queue
import tkinter as tk

LEVEL_COLORS = {
    'SILLY': '#a855f7',
    'DEBUG': '#06b6d4',
    'INFO': '#22c55e',
    'WARN': '#eab308',
    'ERROR': '#ef4444',
}


class TkLogBridge:
    def __init__(self, text_widget: tk.Text, root: tk.Misc, poll_ms: int = 100):
        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._text_widget = text_widget
        self._root = root
        self._poll_ms = poll_ms

        for level_name, color in LEVEL_COLORS.items():
            self._text_widget.tag_config(level_name, foreground=color)

    def on_log(self, level_name: str, message: str) -> None:
        """Safe to call from any thread — just enqueues, no Tk calls here."""
        self._queue.put((level_name, message))

    def start_polling(self) -> None:
        self._drain()

    def _drain(self) -> None:
        try:
            while True:
                level_name, message = self._queue.get_nowait()
                self._text_widget.insert(tk.END, f"[{level_name}] {message}\n", level_name)
                self._text_widget.see(tk.END)
        except queue.Empty:
            pass
        self._root.after(self._poll_ms, self._drain)
