#!/usr/bin/env python3
"""Launches the Wingspan Automation Tkinter GUI."""

import tkinter as tk

from wingspan_gui.gui.app import App

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
