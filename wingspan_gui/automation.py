"""Core automation loop: capture, OCR, score, and reload-or-keep the hand."""

import threading
import time
from pathlib import Path

from PIL import ImageDraw

from wingspan_gui import platform_io
from wingspan_gui.bird_matching import match_bird_name_to_bird
from wingspan_gui.clicking import click_button_sequence, reload_wingspan
from wingspan_gui.config import SCREENSHOT_DIR
from wingspan_gui.ocr import crop_region_and_check_ocr


def manage_screenshots(cfg, logger) -> None:
    """Keep only the most recent SCREENSHOTS_TO_KEEP screenshot sets on disk."""
    full_window_files = list(Path(SCREENSHOT_DIR).glob('full_window_*.png'))
    annotated_files = list(Path(SCREENSHOT_DIR).glob('annotated_*.png'))
    all_files = full_window_files + annotated_files

    timestamps = set()
    for f in full_window_files:
        parts = f.stem.split('_')
        if len(parts) >= 3:
            timestamps.add('_'.join(parts[-2:]))

    timestamps_to_keep = set(sorted(timestamps, reverse=True)[:cfg.tunables.screenshots_to_keep])

    deleted_count = 0
    for f in all_files:
        parts = f.stem.split('_')
        if len(parts) >= 3:
            timestamp = '_'.join(parts[-2:])
            if timestamp not in timestamps_to_keep:
                logger.color_debug(f"Deleting old screenshot: {f}")
                f.unlink()
                deleted_count += 1

    if deleted_count > 0:
        logger.color_debug(f"Deleted {deleted_count} old screenshot(s)")


def annotate_screenshot(cfg, full_img, timestamp, logger) -> str:
    """Save a copy of the screenshot with colored rectangles over bird and EOR regions."""
    logger.color_debug("Creating annotated image for debug")

    img_width, img_height = full_img.size
    draw = ImageDraw.Draw(full_img)

    for region in cfg.starting_birds + cfg.eor_goals:
        x = int(region.x * img_width)
        y = int(region.y * img_height)
        w = int(region.w * img_width)
        h = int(region.h * img_height)
        draw.rectangle([(x, y), (x + w, y + h)], outline=tuple(region.color), width=3)

    annotated_file = f"{SCREENSHOT_DIR}/annotated_{timestamp}.png"
    full_img.save(annotated_file)
    logger.color_debug(f"Saved annotated screenshot: {annotated_file}")

    return annotated_file


def check_score_and_reload(cfg, stop_event: threading.Event, logger, counter: int,
                            continue_on_match: bool = True, automa: bool = False) -> bool:
    """
    Take a screenshot of the End-of-Round goal, starting hand, and tray, then
    reload the game unless the combined bird + EOR points reach cfg.point_threshold.

    Returns:
        bool: True if the game should continue reloading, False if the automation should stop
    """
    logger.color_info(f"ReloadUntilThresholdMet iteration {counter}")

    full_img = None
    timestamp = None
    eor_points = 0
    eor_1_result = ""
    matched_birds = None

    for attempt in range(2):
        if stop_event.is_set():
            logger.color_warn("STOP - stop requested")
            return False

        if stop_event.wait(timeout=cfg.tunables.window_ready_delay):
            return False

        timestamp = time.strftime('%Y%m%d_%H%M%S')
        Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)

        full_img = platform_io.take_screenshot(cfg.window.x_offset, cfg.window.y_offset,
                                                cfg.window.width, cfg.window.height)
        full_window_file = f"{SCREENSHOT_DIR}/full_window_{timestamp}.png"
        full_img.save(full_window_file)
        logger.color_debug(f"Captured full window screenshot: {full_window_file}")

        eor_1_result = crop_region_and_check_ocr(full_img, timestamp, cfg.eor_goals[0], logger, delete_temp_file=False)
        eor_2_result = crop_region_and_check_ocr(full_img, timestamp, cfg.eor_goals[1], logger, delete_temp_file=False)
        has_no_goal = 'NO GOAL' in eor_1_result or 'NO GOAL' in eor_2_result
        eor_points = cfg.no_goal_points if has_no_goal else 0
        logger.color_info(f"EOR is '{eor_1_result}' (NO GOAL: {has_no_goal}, {eor_points} points)")

        bird_results = {}
        for bird in cfg.starting_birds + cfg.tray_birds:
            logger.color_debug(f"Processing {bird.name}")
            bird_result = crop_region_and_check_ocr(full_img, timestamp, bird, logger)
            bird_results[bird.name] = bird_result
            logger.color_silly(f"OCR result for {bird.name}: '{bird_result}'")

        matched_birds = match_bird_name_to_bird(list(bird_results.values()),
                                                 cfg.tunables.bird_match_minimum_ratio, logger)
        if (not matched_birds) or all(b['match'] is None for b in matched_birds):
            logger.color_error("CRITICAL: No bird names were matched successfully. It's possible the screenshot was bad.")
            if attempt == 0:
                logger.color_error("trying again")
                continue
            else:
                logger.color_error("This has already been tried again")
                return False
        else:
            break

    for match in matched_birds:
        logger.color_silly(f"Matched '{match['name']}' to '{match['match']}' (ratio: {match['ratio']:.2f})")

    bird_list = " - ".join([
        match['match'] if match['match'] is not None else f"UNKNOWN({match['name']})"
        for match in matched_birds
    ])
    logger.color_info(f"Hand and tray birds are: {bird_list}")

    normalized_bird_points = {name.upper(): points for name, points in cfg.bird_points.items()}
    matched_target_birds = [match['match'] for match in matched_birds
                             if match['match'] and match['match'].upper() in normalized_bird_points]
    bird_points = sum(normalized_bird_points[name.upper()] for name in matched_target_birds)

    total_points = eor_points + bird_points
    logger.color_info(f"Points: {bird_points} (birds: {', '.join(matched_target_birds) or 'none'}) + {eor_points} (EOR) = {total_points} / {cfg.point_threshold}")

    if total_points >= cfg.point_threshold:
        logger.color_warn(f"Threshold met with {total_points} points")

        if logger.current_level <= logger.DEBUG:
            annotate_screenshot(cfg, full_img.copy(), timestamp, logger)

        if continue_on_match:
            click_button_sequence(cfg, ['firstBird', 'secondBird', 'thirdBird', 'fourthBird', 'fifthBird',
                                         'forwardArrowButtonShort', 'firstBonusCard', 'forwardArrowButton'],
                                   stop_event, logger)
            manage_screenshots(cfg, logger)
            reload_wingspan(cfg, stop_event, logger, automa)
            return True
        else:
            logger.color_warn("STOP - Threshold met, ending automation")
            platform_io.play_alert_sound(cfg.alert_sound_macos, cfg.alert_sound_windows)
            manage_screenshots(cfg, logger)
            return False

    manage_screenshots(cfg, logger)
    reload_wingspan(cfg, stop_event, logger, automa)
    return True


def reload_until_threshold_met(cfg, stop_event: threading.Event, logger,
                                continue_on_match: bool | None = None,
                                automa: bool | None = None) -> None:
    """
    Main automation loop that continuously reloads the Wingspan game until
    the combined bird + EOR points reach cfg.point_threshold.

    Press Esc or Ctrl+C to stop the automation at any time.
    """
    if continue_on_match is None:
        continue_on_match = cfg.run_options.continue_on_match
    if automa is None:
        automa = cfg.run_options.automa

    logger.color_info(f"Starting ReloadUntilThresholdMet (threshold: {cfg.point_threshold}) (Press Esc or Ctrl+C to stop)")
    counter = 0

    try:
        while not stop_event.is_set():
            should_continue = check_score_and_reload(cfg, stop_event, logger, counter,
                                                       continue_on_match=continue_on_match, automa=automa)
            if not should_continue:
                break
            counter += 1
            logger.color_debug(f"Completed iteration {counter}, continuing...")
    except KeyboardInterrupt:
        logger.color_warn("Emergency stop requested - stopping automation")
        stop_event.set()

    logger.color_info("ReloadUntilThresholdMet complete")
