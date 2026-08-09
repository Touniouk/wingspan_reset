#!/usr/bin/env python3
"""
CLI entry point for the cross-platform Wingspan automation core.
Reproduces the behavior of wingspan_automation.py, reading settings from a
saved config.json (see wingspan_gui/config.py) instead of hardcoded constants.
"""

import threading
import time

from logger import Logger  # type: ignore

from wingspan_gui.automation import reload_until_threshold_met
from wingspan_gui.config import AppConfig, DEFAULT_LOG_PATH
from wingspan_gui.platform_io import GlobalHotkeyListener

TEST_COUNTDOWN_SECONDS = 3

if __name__ == "__main__":
    cfg = AppConfig.load()
    logger = Logger(level=Logger.SILLY, log_file=str(DEFAULT_LOG_PATH), enable_color_in_file=True)

    stop_event = threading.Event()
    hotkey = GlobalHotkeyListener(stop_event)
    hotkey.start()

    logger.color_info(f"Starting in {TEST_COUNTDOWN_SECONDS} seconds... Focus the Wingspan window!")
    time.sleep(TEST_COUNTDOWN_SECONDS)

    reload_until_threshold_met(cfg, stop_event, logger)

    hotkey.stop()
