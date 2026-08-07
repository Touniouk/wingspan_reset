#!/usr/bin/env python3
"""Simple autoclicker that clicks at the current mouse position at a fixed rate.
Press Cmd+X to toggle clicking on/off. Press Esc to quit."""

import pyautogui # type: ignore
import time
from pynput import keyboard # type: ignore

CLICKS_PER_SECOND = 2
MAX_CLICKS_PER_UNPAUSE = 187

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
        print("Clicking ON" if clicking_enabled else "Clicking OFF")
    elif key == keyboard.Key.esc:
        exit_requested = True
        return False  # stop the listener

def on_release(key):
    global cmd_pressed
    if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
        cmd_pressed = False

def autoclick():
    global clicking_enabled, clicks_since_unpause

    delay = 1 / CLICKS_PER_SECOND
    print(f"Ready. Cmd+X toggles clicking ({CLICKS_PER_SECOND}/sec, max {MAX_CLICKS_PER_UNPAUSE} per unpause) on/off. Esc quits.")

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    while not exit_requested:
        if clicking_enabled:
            pyautogui.click()
            clicks_since_unpause += 1
            if clicks_since_unpause >= MAX_CLICKS_PER_UNPAUSE:
                clicking_enabled = False
                print(f"Reached {MAX_CLICKS_PER_UNPAUSE} clicks, auto-pausing")
        time.sleep(delay)

    listener.stop()
    print("Exited.")

if __name__ == "__main__":
    autoclick()
