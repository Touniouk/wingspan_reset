"""OS-specific pieces: screenshot capture, alert sound, and the emergency-stop hotkey."""

import platform
import subprocess
import threading

import pyautogui  # type: ignore
from PIL import Image
from pynput import keyboard  # type: ignore

_display_scale_cache: float | None = None


def _get_display_scale() -> float:
    """Ratio between a full-screen screenshot's pixel size and pyautogui's logical
    screen size (e.g. 2.0 on a Retina display, ~1.0 on an unscaled display)."""
    global _display_scale_cache
    if _display_scale_cache is None:
        logical_w, _ = pyautogui.size()
        full_shot = pyautogui.screenshot()
        _display_scale_cache = full_shot.size[0] / logical_w
    return _display_scale_cache


def take_screenshot(x: int, y: int, w: int, h: int) -> Image.Image:
    """
    Capture a region of the screen and return it at the same pixel density
    `screencapture -R` would have produced (upscaling to match the display's
    scale factor, since pyautogui.screenshot() returns exactly w x h pixels
    regardless of HiDPI scaling).
    """
    img = pyautogui.screenshot(region=(x, y, w, h))
    scale = _get_display_scale()
    if scale != 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return img


def play_alert_sound(macos_path: str, windows_path: str | None = None) -> None:
    """Play a system alert sound to notify the user the automation has stopped."""
    system = platform.system()
    if system == "Darwin":
        subprocess.run(['afplay', macos_path], check=False)
    elif system == "Windows":
        import winsound
        if windows_path:
            winsound.PlaySound(windows_path, winsound.SND_FILENAME)
        else:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    else:
        print('\a')


class GlobalHotkeyListener:
    """Listens for a global Esc key press and sets a shared stop_event, regardless
    of which window has focus. Modeled on the pattern used in autoclicker.py."""

    def __init__(self, stop_event: threading.Event):
        self._stop_event = stop_event
        self._listener: keyboard.Listener | None = None

    def _on_press(self, key):
        if key == keyboard.Key.esc:
            self._stop_event.set()

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None
