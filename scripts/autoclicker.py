#!/usr/bin/env python3
"""Simple autoclicker with a small GUI. Clicks at the current mouse position at a
fixed rate, up to a configurable number of clicks per Start.
Cmd+A toggles clicking on/off from anywhere. Esc quits. Or use the buttons below."""

import tkinter as tk
from tkinter import ttk

import pyautogui  # type: ignore
from pynput import keyboard  # type: ignore

CLICKS_PER_SECOND = 2
DEFAULT_MAX_CLICKS = 200

clicking_enabled = False
exit_requested = False
cmd_pressed = False
clicks_since_unpause = 0

def on_press(key):
    global clicking_enabled, exit_requested, cmd_pressed, clicks_since_unpause

    if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
        cmd_pressed = True
    elif key == keyboard.KeyCode.from_char('a') and cmd_pressed:
        clicking_enabled = not clicking_enabled
        if clicking_enabled:
            clicks_since_unpause = 0
    elif key == keyboard.Key.esc:
        exit_requested = True
        return False  # stop the listener

def on_release(key):
    global cmd_pressed
    if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
        cmd_pressed = False

class AutoclickerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Autoclicker")

        param_grid = ttk.Frame(root)
        param_grid.pack(padx=12, pady=6, fill="x")
        ttk.Label(param_grid, text="Max clicks:").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
        self.max_clicks_var = tk.IntVar(value=DEFAULT_MAX_CLICKS)
        ttk.Spinbox(param_grid, from_=1, to=10000, textvariable=self.max_clicks_var, width=8).grid(row=0, column=1, padx=6)

        ttk.Label(param_grid, text="Clicks per second:").grid(row=1, column=0, sticky="w", padx=12, pady=(6, 12))
        self.clicks_per_second_var = tk.IntVar(value=CLICKS_PER_SECOND)
        ttk.Spinbox(param_grid, from_=1, to=100, textvariable=self.clicks_per_second_var, width=8).grid(row=1, column=1, padx=6, pady=(6, 12))

        button_row = ttk.Frame(root)
        button_row.pack(padx=12, pady=6, fill="x")
        self.start_button = ttk.Button(button_row, text="Start", command=self.start)
        self.start_button.pack(side="left", padx=4)
        self.stop_button = ttk.Button(button_row, text="Stop", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=4)

        self.countdown_label = ttk.Label(root, text="Remaining clicks: -")
        self.countdown_label.pack(padx=12, pady=8)

        ttk.Label(
            root,
            text="Cmd+A toggles clicking on/off from anywhere.\nEsc quits. Or use the buttons above.",
            justify="center",
        ).pack(padx=12, pady=(0, 12))

        root.protocol("WM_DELETE_WINDOW", self.quit)
        self._tick()

    def start(self):
        global clicking_enabled, clicks_since_unpause
        clicking_enabled = True
        clicks_since_unpause = 0

    def stop(self):
        global clicking_enabled
        clicking_enabled = False

    def quit(self):
        global exit_requested
        exit_requested = True
        self.root.destroy()

    def _tick(self):
        global clicking_enabled, clicks_since_unpause

        if exit_requested:
            self.root.destroy()
            return

        if clicking_enabled:
            pyautogui.click()
            clicks_since_unpause += 1
            max_clicks = self.max_clicks_var.get()
            remaining = max(0, max_clicks - clicks_since_unpause)
            self.countdown_label.config(text=f"Remaining clicks: {remaining}")
            if clicks_since_unpause >= max_clicks:
                clicking_enabled = False
        else:
            self.countdown_label.config(text="Remaining clicks: -")

        self.start_button.config(state="disabled" if clicking_enabled else "normal")
        self.stop_button.config(state="normal" if clicking_enabled else "disabled")

        self.root.after(int(1000 / CLICKS_PER_SECOND), self._tick)


if __name__ == "__main__":
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    root = tk.Tk()
    app = AutoclickerApp(root)
    root.mainloop()

    listener.stop()
