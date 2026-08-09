"""Converts fractional button coordinates to screen pixels and clicks through them."""

import threading

import pyautogui  # type: ignore

from wingspan_gui.config import WindowConfig


def get_coord(window: WindowConfig, xr: float, yr: float) -> tuple[int, int]:
    """Convert relative window coordinates (0.0-1.0) to absolute screen coordinates."""
    x = int(window.width * xr + window.x_offset)
    y = int(window.height * yr + window.y_offset - window.dead_height)
    return (x, y)


def click_button_sequence(cfg, button_sequence: list[str], stop_event: threading.Event, logger) -> None:
    """
    Execute a sequence of button clicks with delays between each click. Each
    delay is an interruptible wait, so stop_event.set() takes effect immediately
    even mid-sequence instead of only at the next iteration boundary.
    """
    logger.color_debug(f"Starting button sequence with {len(button_sequence)} steps")

    for i, key in enumerate(button_sequence, 1):
        button = cfg.buttons[key]
        point = get_coord(cfg.window, button.x, button.y)
        logger.color_silly(f"Step {i}/{len(button_sequence)}: {key} (delay: {button.delay}s, coord: {point})")
        pyautogui.click(point[0], point[1])
        if stop_event.wait(timeout=button.delay):
            logger.color_debug("Button sequence interrupted by stop request")
            return

    logger.color_debug("Button sequence complete")


def reload_wingspan(cfg, stop_event: threading.Event, logger, automa: bool = False) -> None:
    """
    Execute the full Wingspan game reload sequence by clicking through
    the settings menu, play button, and game setup screens.
    """
    logger.color_info("Reloading Wingspan")

    if automa:
        button_sequence = ['settingsButton', 'menuButton', 'playButton', 'automaButton',
                            'forwardArrowButton', 'middleButton', 'wetlandHabitatButton']
    else:
        button_sequence = ['settingsButton', 'menuButton', 'playButton', 'customGameButton',
                            'forwardArrowButton', 'middleButton', 'wetlandHabitatButton']
    click_button_sequence(cfg, button_sequence, stop_event, logger)
