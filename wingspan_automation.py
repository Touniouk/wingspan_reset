#!/usr/bin/env python3
"""
Wingspan game automation script that repeatedly reloads the game until
the combined point value of detected birds and the End-of-Round (EOR) goal,
read via OCR, meets a configurable threshold.
"""

import pyautogui # type: ignore
import time
import subprocess
import os
from pathlib import Path
from logger import Logger # type: ignore
from PIL import Image, ImageDraw # type: ignore
import json
from difflib import SequenceMatcher, get_close_matches
import unicodedata

#################################################
############ PARAMETER CONFIGURATION ############
#################################################

############ YOU MUST CHANGE THOSE VALUES TO MATCH YOUR SCREEN RESOLUTION AND WINDOW POSITION ############

# Configuration
DEAD_HEIGHT_WINDOW = 30
WINDOW_X_OFFSET = 6
WINDOW_Y_OFFSET = 43
WINDOW_W = 1280
WINDOW_H = 828
SCREENSHOT_DIR = "screenshots"
BIRD_JSON = "birds.json"
LOG_FILE = '/tmp/custom.log'

############ FEEL FREE TO CHANGE THESE VALUES IF YOU WANT TO TWEAK THE AUTOMATION ############

SCREENSHOTS_TO_KEEP = 3                                 # How many past screenshot sets (full_window + annotated) to keep on disk
TEST_COUNTDOWN_SECONDS = 3                              # Seconds to count down before taking a screenshot in the test/calibration helpers
ALERT_SOUND_PATH = '/System/Library/Sounds/Glass.aiff'  # Sound file played by play_alert_sound() when the automation stops

# Point value for each desirable bird if found in the hand or tray
birdPoints = {
    "Canvasback": 2,
    "Savi's Warbler": 2,
    "Northern Shoveler": 2,
    "Purple Gallinule": 2,
    "Spotted Sandpiper": 2,
    "Wilson's Snipe": 2,
    "Kelp Gull": 1,
    "Brolga": 1,
    "Dorian's Jackdaw": 1,
    "Nightingale": 1,
    "Green Pheasant": 1,
    "Gray Catbird": 1,
    "Northern Mockingbird": 1,
    "Bluethroat": 1,
}
NO_GOAL_POINTS = 100  # Point value awarded when the "NO GOAL" End-of-Round goal is detected
POINT_THRESHOLD = 104 # Hand is kept once the combined bird + EOR points reach this value

############ PROBABLY DON'T CHANGE THESE VALUES UNLESS YOU KNOW WHAT YOU'RE DOING ############

BIRD_MATCH_MINIMUM_RATIO = 0.6  # Minimum fuzzy-match confidence (0-1) for an OCR'd name to count as a bird match
WINDOW_READY_DELAY = 0.2        # Seconds to wait after a click sequence before capturing a screenshot, so the window can settle
GRID_SPACING_PX = 100           # Pixel spacing between grid lines in create_coordinate_grid

##############################
############ CODE ############
##############################

# Create custom logger instance
logger = Logger(level=Logger.SILLY, log_file=LOG_FILE, enable_color_in_file=True)

buttons = {
    'settingsButton': {'delay': 0.6, 'point': (56/WINDOW_W, 110/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'menuButton': {'delay': 2.0, 'point': (634/WINDOW_W, 545/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'playButton': {'delay': 0.4, 'point': (345/WINDOW_W, 465/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'customGameButton': {'delay': 0.4, 'point': (328/WINDOW_W, 688/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'automaButton': {'delay': 0.4, 'point': (630/WINDOW_W, 688/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    # 'forwardArrowButton': {'delay': 5.4, 'point': (1198/WINDOW_W, 844/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'forwardArrowButton': {'delay': 6.0, 'point': (1198/WINDOW_W, 844/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'forwardArrowButtonShort': {'delay': 0.5, 'point': (1198/WINDOW_W, 844/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'middleButton': {'delay': 0.2, 'point': (640/WINDOW_W, 510/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'wetlandHabitatButton': {'delay': 0.4, 'point': (60/WINDOW_W, 600/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'firstBird': {'delay': 0.3, 'point': (316/WINDOW_W, 400/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'secondBird': {'delay': 0.3, 'point': (480/WINDOW_W, 400/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'thirdBird': {'delay': 0.3, 'point': (630/WINDOW_W, 400/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'fourthBird': {'delay': 0.3, 'point': (790/WINDOW_W, 400/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'fifthBird': {'delay': 0.3, 'point': (950/WINDOW_W, 400/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'firstBonusCard': {'delay': 0.3, 'point': (510/WINDOW_W, 400/(WINDOW_H+DEAD_HEIGHT_WINDOW))},
    'secondBonusCard': {'delay': 0.3, 'point': (740/WINDOW_W, 400/(WINDOW_H+DEAD_HEIGHT_WINDOW))}
}

startingBirds = [
    {'name': 'bird 1', 'rect': { 'x': (260 / WINDOW_W), 'y': (265 / WINDOW_H), 'w': (104 / WINDOW_W), 'h': (44 / WINDOW_H) }, 'color': (255, 0, 0)},      # Red
    {'name': 'bird 2', 'rect': { 'x': (436 / WINDOW_W), 'y': (265 / WINDOW_H), 'w': (104 / WINDOW_W), 'h': (44 / WINDOW_H) }, 'color': (0, 255, 0)},      # Green
    {'name': 'bird 3', 'rect': { 'x': (590 / WINDOW_W), 'y': (265 / WINDOW_H), 'w': (104 / WINDOW_W), 'h': (44 / WINDOW_H) }, 'color': (0, 0, 255)},      # Blue
    {'name': 'bird 4', 'rect': { 'x': (744 / WINDOW_W), 'y': (265 / WINDOW_H), 'w': (104 / WINDOW_W), 'h': (44 / WINDOW_H) }, 'color': (255, 255, 0)},    # Yellow
    {'name': 'bird 5', 'rect': { 'x': (911 / WINDOW_W), 'y': (265 / WINDOW_H), 'w': (104 / WINDOW_W), 'h': (44 / WINDOW_H) }, 'color': (255, 0, 255)}     # Magenta
]

trayBirds = [
    {'name': 'tray bird 1', 'rect': { 'x': (700 / WINDOW_W), 'y': (580 / WINDOW_H), 'w': (104 / WINDOW_W), 'h': (44 / WINDOW_H) }, 'color': (255, 0, 0)},      # Red
    {'name': 'tray bird 2', 'rect': { 'x': (833 / WINDOW_W), 'y': (580 / WINDOW_H), 'w': (104 / WINDOW_W), 'h': (44 / WINDOW_H) }, 'color': (0, 255, 0)},      # Green
    {'name': 'tray bird 3', 'rect': { 'x': (970 / WINDOW_W), 'y': (580 / WINDOW_H), 'w': (104 / WINDOW_W), 'h': (44 / WINDOW_H) }, 'color': (0, 0, 255)},      # Blue
]

endOfRoundGoals = [
    {'name': 'eor1', 'rect': { 'x': (995 / WINDOW_W), 'y': (62 / WINDOW_H), 'w': (60 / WINDOW_W), 'h': (65 / WINDOW_H) }, 'color': (0, 255, 255)},      # Cyan
    {'name': 'eor2', 'rect': { 'x': (1061 / WINDOW_W), 'y': (45 / WINDOW_H), 'w': (60 / WINDOW_W), 'h': (65 / WINDOW_H) }, 'color': (255, 128, 0)},     # Orange
    {'name': 'eor3', 'rect': { 'x': (1124 / WINDOW_W), 'y': (45 / WINDOW_H), 'w': (60 / WINDOW_W), 'h': (65 / WINDOW_H) }, 'color': (128, 0, 255)},     # Purple
    {'name': 'eor4', 'rect': { 'x': (1185 / WINDOW_W), 'y': (45 / WINDOW_H), 'w': (60 / WINDOW_W), 'h': (65 / WINDOW_H) }, 'color': (255, 128, 128)}    # Pink
]

def is_caps_lock_on():
    """
    Check if Caps Lock is currently active on macOS.
    
    Returns:
        bool: True if Caps Lock is on, False otherwise
    """
    try:
        result = subprocess.run(
            ['python3', '-c', 
             'import Quartz; print(Quartz.CGEventSourceFlagsState(Quartz.kCGEventSourceStateCombinedSessionState) & Quartz.kCGEventFlagMaskAlphaShift != 0)'],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() == 'True'
    except:
        return False

def play_alert_sound():
    """Play a system alert sound to notify the user the script has stopped."""
    subprocess.run(['afplay', ALERT_SOUND_PATH])

def manage_screenshots():
    """
    Keep only the last 3 full window screenshots and their annotated counterparts.
    Deletes older screenshots from the main SCREENSHOT_DIR.
    """
    # Get all full window screenshot files
    full_window_files = list(Path(SCREENSHOT_DIR).glob('full_window_*.png'))
    annotated_files = list(Path(SCREENSHOT_DIR).glob('annotated_*.png'))
    
    # Combine and sort by modification time (newest first)
    all_files = full_window_files + annotated_files
    all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Group files by timestamp (full_window and annotated pairs)
    timestamps = set()
    for f in full_window_files:
        # Extract timestamp from filename: full_window_20250929_123456.png
        parts = f.stem.split('_')
        if len(parts) >= 3:
            timestamp = '_'.join(parts[-2:])  # Get last two parts (date_time)
            timestamps.add(timestamp)
    
    # Sort timestamps (newest first)
    timestamps = sorted(timestamps, reverse=True)

    # Keep only the most recent timestamps
    timestamps_to_keep = set(timestamps[:SCREENSHOTS_TO_KEEP])
    
    # Delete files that don't match the kept timestamps
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

def get_coord(xr, yr):
    """
    Convert relative window coordinates to absolute screen coordinates.
    
    Args:
        xr (float): Relative x coordinate (0.0 to 1.0)
        yr (float): Relative y coordinate (0.0 to 1.0)
    
    Returns:
        tuple: (x, y) absolute screen coordinates
    """
    x = int(WINDOW_W * xr + WINDOW_X_OFFSET)
    y = int(WINDOW_H * yr + WINDOW_Y_OFFSET - DEAD_HEIGHT_WINDOW)
    return (x, y)

def perform_ocr_local(filename):
    """
    Use tesseract (local OCR) to extract text from an image.
    
    Args:
        filename (str): Path to the image file to process
    
    Returns:
        str: Normalized OCR result (uppercase, no whitespace) or "Nothing" on failure
    """
    logger.color_debug("Performing OCR with tesseract for file: " + filename)
    
    try:
        # PSM (Page Segmentation Mode) options:
        # 3 = Fully automatic (default)
        # 6 = Uniform block of text
        # 7 = Single text line
        # 8 = Single word
        # 13 = Raw line (for single line without orientation/script detection)
        
        result = subprocess.run(
            ['tesseract', filename, 'stdout',
             '--psm', '6',  # Uniform block of text
             '--oem', '3',  # Use LSTM neural net (most accurate)
             '-c', 'tessedit_char_blacklist=0123456789!@#$%^&*()'  # Block unwanted chars
            ],
            capture_output=True,
            text=True,
            check=True
        )
        text = result.stdout
        normalized = ' '.join(text.split()).upper()
        logger.color_debug(f"OCR result: '{normalized}'")
        return normalized
    except subprocess.CalledProcessError as e:
        logger.color_error(f"OCR failed: {e}")
        return "Nothing"

def click_button_sequence(button_sequence):
    """
    Execute a sequence of button clicks with specified delays between each click.
    
    Args:
        buttons (list): List of dictionaries containing 'name', 'delay', and 'point' keys
                       where 'point' is a tuple (x, y) of screen coordinates
    """
    logger.color_debug(f"Starting button sequence with {len(button_sequence)} steps")

    # Create list with converted coordinates
    converted_buttons = [
        {**buttons[key], 'name': key, 'point': get_coord(*buttons[key]['point'])}
        for key in button_sequence
    ]

    # Click each button in sequence
    for i, button in enumerate(converted_buttons, 1):
        logger.color_silly(f"Step {i}/{len(converted_buttons)}: {button['name']} (delay: {button['delay']}s, coord: {button['point']})")
        pyautogui.click(button['point'][0], button['point'][1])
        time.sleep(button['delay'])

    logger.color_debug("Button sequence complete")

def reload_wingspan(automa=False):
    """
    Execute the full Wingspan game reload sequence by clicking through
    the settings menu, play button, and game setup screens.
    """
    logger.color_info("Reloading Wingspan")

    # Define the sequence of button keys to use
    if automa:
        button_sequence = ['settingsButton', 'menuButton', 'playButton', 'automaButton', 'forwardArrowButton', 'middleButton', 'wetlandHabitatButton']
    else:
        button_sequence = ['settingsButton', 'menuButton', 'playButton', 'customGameButton', 'forwardArrowButton', 'middleButton', 'wetlandHabitatButton']
    click_button_sequence(button_sequence)

def crop_region_and_check_ocr(full_img, timestamp, region, delete_temp_file=True):
    """
    Crop a specified region from the full image and perform OCR.

    Args:
        full_img (PIL.Image): The full screenshot image
        timestamp (str): Timestamp string for the filename
        region (dict): The region dictionary containing 'name' and 'rect' keys

    Returns:
        str: The OCR result for the specified region
    """
    # Get the dimensions of the full image
    img_width, img_height = full_img.size

    # Crop and OCR the specified region
    x = int(region['rect']['x'] * img_width)
    y = int(region['rect']['y'] * img_height)
    w = int(region['rect']['w'] * img_width)
    h = int(region['rect']['h'] * img_height)

    # Crop the region to temp file for OCR
    region_crop = full_img.crop((x, y, x + w, y + h))
    region_crop_file = f"{SCREENSHOT_DIR}/temp_region_{region['name']}_{timestamp}.png"
    region_crop.save(region_crop_file)

    # Perform OCR on the cropped region
    region_result = perform_ocr_local(region_crop_file)

    # Clean up temp file
    if delete_temp_file:
        Path(region_crop_file).unlink(missing_ok=True)

    return region_result

def remove_accents(text):
    """
    Remove accents/diacritics from Unicode text.
    
    Args:
        text (str): Text with accented characters
        
    Returns:
        str: Text with accents removed
    """
    # Normalize to NFD (decomposed form)
    nfd = unicodedata.normalize('NFD', text)
    # Filter out combining characters (the accents)
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')

def annotate_screenshot(full_img, timestamp):
    """
    Create an annotated version of a screenshot with colored rectangles around bird and EOR regions.
    
    Args:
        full_img (PIL.Image): The full window screenshot image
        timestamp (str): Timestamp string for the filename
        
    Returns:
        str: Path to the saved annotated image
    """
    logger.color_debug("Creating annotated image for debug")
    
    img_width, img_height = full_img.size
    draw = ImageDraw.Draw(full_img)
    
    # Draw rectangles for birds
    for bird in startingBirds:
        bx = int(bird['rect']['x'] * img_width)
        by = int(bird['rect']['y'] * img_height)
        bw = int(bird['rect']['w'] * img_width)
        bh = int(bird['rect']['h'] * img_height)
        draw.rectangle(
            [(bx, by), (bx + bw, by + bh)],
            outline=bird['color'],
            width=3
        )
    
    # Draw rectangles for EORs
    for eor in endOfRoundGoals:
        ex = int(eor['rect']['x'] * img_width)
        ey = int(eor['rect']['y'] * img_height)
        ew = int(eor['rect']['w'] * img_width)
        eh = int(eor['rect']['h'] * img_height)
        draw.rectangle(
            [(ex, ey), (ex + ew, ey + eh)],
            outline=eor['color'],
            width=3
        )
    
    # Save annotated image in main SCREENSHOT_DIR
    annotated_file = f"{SCREENSHOT_DIR}/annotated_{timestamp}.png"
    full_img.save(annotated_file)
    logger.color_debug(f"Saved annotated screenshot: {annotated_file}")
    
    return annotated_file

def check_score_and_reload(counter, tryAgain=True, continue_on_match=True, automa=False):
    """
    Take a screenshot of the End-of-Round goal, starting hand, and tray, then
    reload the game unless the combined bird + EOR points reach POINT_THRESHOLD.

    Args:
        counter (int): The current iteration number (for logging purposes)
        tryAgain (bool): Whether to retry on OCR failure
        continue_on_match (bool): If True, select the birds and keep reloading when
                                   the point threshold is met. If False, stop the
                                   automation and play an alert sound instead.
        automa (bool): Whether to reload into an Automa game instead of a custom game.

    Returns:
        bool: True if the game should continue reloading, False if the automation should stop
    """
    logger.color_info(f"ReloadUntilThresholdMet iteration {counter}")

    # Check for caps lock emergency stop
    if is_caps_lock_on():
        logger.color_warn("STOP - Caps Lock is active")
        return False

    # Wait for window to be ready
    time.sleep(WINDOW_READY_DELAY)

    # Take ONE full window screenshot and save to main SCREENSHOT_DIR
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)

    full_window_file = f"{SCREENSHOT_DIR}/full_window_{timestamp}.png"
    cmd = f"screencapture -R{WINDOW_X_OFFSET},{WINDOW_Y_OFFSET},{WINDOW_W},{WINDOW_H} {full_window_file}"
    subprocess.run(cmd, shell=True)
    logger.color_debug(f"Captured full window screenshot: {full_window_file}")

    full_img = Image.open(full_window_file)

    # Check the EOR regions for "NO GOAL"
    eor_1_result = crop_region_and_check_ocr(full_img, timestamp, endOfRoundGoals[0], False)
    eor_2_result = crop_region_and_check_ocr(full_img, timestamp, endOfRoundGoals[1], False)
    has_no_goal = 'NO GOAL' in eor_1_result or 'NO GOAL' in eor_2_result
    eor_points = NO_GOAL_POINTS if has_no_goal else 0
    logger.color_info(f"EOR is '{eor_1_result}' (NO GOAL: {has_no_goal}, {eor_points} points)")

    # OCR every hand and tray bird region
    bird_results = {}
    for bird in startingBirds + trayBirds:
        bird_name = bird['name']
        logger.color_debug(f"Processing {bird_name}")

        bird_result = crop_region_and_check_ocr(full_img, timestamp, bird)
        bird_results[bird_name] = bird_result
        logger.color_silly(f"OCR result for {bird_name}: '{bird_result}'")

    # Match bird names to known birds using fuzzy matching
    matched_birds = match_bird_name_to_bird(list(bird_results.values()))
    if (not matched_birds) or all(bird['match'] is None for bird in matched_birds):
        logger.color_error("CRITICAL: No bird names were matched successfully. It's possible the screenshot was bad.")
        if tryAgain:
            logger.color_error("trying again")
            return check_score_and_reload(counter, False, continue_on_match, automa)
        else:
            logger.color_error("This has already been tried again")
            return False

    for match in matched_birds:
        logger.color_silly(f"Matched '{match['name']}' to '{match['match']}' (ratio: {match['ratio']:.2f})")

    # Format the results
    bird_list = " - ".join([
        match['match'] if match['match'] is not None else f"UNKNOWN({match['name']})"
        for match in matched_birds
    ])
    logger.color_info(f"Hand and tray birds are: {bird_list}")

    # Sum points for every matched bird that's in birdPoints (duplicates count each time)
    normalized_bird_points = {name.upper(): points for name, points in birdPoints.items()}
    matched_target_birds = [match['match'] for match in matched_birds if match['match'] and match['match'].upper() in normalized_bird_points]
    bird_points = sum(normalized_bird_points[name.upper()] for name in matched_target_birds)

    total_points = eor_points + bird_points
    logger.color_info(f"Points: {bird_points} (birds: {', '.join(matched_target_birds) or 'none'}) + {eor_points} (EOR) = {total_points} / {POINT_THRESHOLD}")

    if total_points >= POINT_THRESHOLD:
        logger.color_warn(f"Threshold met with {total_points} points")

        # If debug level, create annotated image
        if logger.current_level <= Logger.DEBUG:
            annotate_screenshot(full_img.copy(), timestamp)

        if continue_on_match:
            # Select every bird in the starting hand so the game is kept, then reload again
            click_button_sequence(['firstBird', 'secondBird', 'thirdBird', 'fourthBird', 'fifthBird', 'forwardArrowButtonShort', 'firstBonusCard', 'forwardArrowButton'])

            manage_screenshots()
            reload_wingspan(automa)
            return True
        else:
            logger.color_warn("STOP - Threshold met, ending automation")
            play_alert_sound()
            manage_screenshots()
            return False

    manage_screenshots()
    reload_wingspan(automa)
    return True

def reload_until_threshold_met(continue_on_match=True, automa=False):
    """
    Main automation loop that continuously reloads the Wingspan game until
    the combined bird + EOR points reach POINT_THRESHOLD.

    Args:
        continue_on_match (bool): If True, select the birds and keep reloading when
                                   the point threshold is met. If False, stop the
                                   automation and play an alert sound instead.
        automa (bool): Whether to reload into an Automa game instead of a custom game.

    Press Ctrl+C or enable Caps Lock to stop the automation at any time.
    """
    logger.color_info(f"Starting ReloadUntilThresholdMet (threshold: {POINT_THRESHOLD}) (Press Ctrl+C or Caps Lock to stop)")
    counter = 0

    try:
        while True:
            should_continue = check_score_and_reload(counter, continue_on_match=continue_on_match, automa=automa)
            if not should_continue:
                break
            counter += 1
            logger.color_debug(f"Completed iteration {counter}, continuing...")
    except KeyboardInterrupt:
        logger.color_warn("Emergency stop requested - stopping automation")

    logger.color_info("ReloadUntilThresholdMet complete")

def match_bird_name_to_bird(birdNames):
    """
    Match a list of bird names to known bird names from BIRD_JSON using fuzzy matching.
    """
    birds = []

    with open(BIRD_JSON, 'r', encoding='utf-8') as file:
        data = json.load(file)
        # Normalize both the candidates and the OCR results
        candidates = [(bird['Common name'], remove_accents(bird['Common name'].upper())) 
                      for bird in data]

        for name in birdNames:
            # Remove accents from OCR result
            normalized_name = remove_accents(name)
            
            best_match = None
            best_ratio = 0
            best_original = None

            for original_name, candidate in candidates:
                ratio = SequenceMatcher(None, normalized_name, candidate).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = candidate
                    best_original = original_name

            if not best_match:
                logger.color_error(f"CRITICAL: No match found for bird name: '{name}'")
                birds.append({
                    'name': name,
                    'match': None,
                    'ratio': 0,
                    'error': 'NO_MATCH_FOUND'
                })
            elif best_ratio < BIRD_MATCH_MINIMUM_RATIO:
                logger.color_warn(f"LOW CONFIDENCE: Bird name '{name}' matched to '{best_original}' with ratio {best_ratio:.2f}")
                birds.append({
                    'name': name,
                    'match': best_original,
                    'ratio': best_ratio,
                    'error': 'LOW_CONFIDENCE'
                })
            else:
                logger.color_silly(f"Matched '{name}' to '{best_original}' (confidence: {best_ratio:.2f})")
                birds.append({
                    'name': name,
                    'match': best_original,
                    'ratio': best_ratio,
                    'error': None
                })
                
    return birds

def test_bird_and_eor_coordinates():
    """
    Take one full screenshot and draw colored rectangles around bird and EOR regions.
    """
    logger.color_info(f"Testing bird and EOR coordinates - taking screenshot in {TEST_COUNTDOWN_SECONDS} seconds")
    time.sleep(TEST_COUNTDOWN_SECONDS)
    
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    test_dir = f"{SCREENSHOT_DIR}/coordinate_tests"
    Path(test_dir).mkdir(parents=True, exist_ok=True)
    
    # Capture full window
    full_window_file = f"{test_dir}/full_window_{timestamp}.png"
    cmd = f"screencapture -R{WINDOW_X_OFFSET},{WINDOW_Y_OFFSET},{WINDOW_W},{WINDOW_H} {full_window_file}"
    subprocess.run(cmd, shell=True)
    logger.color_info(f"Captured full window screenshot")
    
    # Load image and prepare to draw
    img = Image.open(full_window_file)
    draw = ImageDraw.Draw(img)
    img_width, img_height = img.size
    
    # Draw rectangles for birds
    logger.color_info("Drawing bird regions...")
    for bird in startingBirds:
        # These coordinates should match exactly what take_screenshot_region uses
        x = int(bird['rect']['x'] * img_width)
        y = int(bird['rect']['y'] * img_height)
        w = int(bird['rect']['w'] * img_width)
        h = int(bird['rect']['h'] * img_height)
        
        # Draw rectangle (left, top, right, bottom)
        draw.rectangle(
            [(x, y), (x + w, y + h)],
            outline=bird['color'],
            width=3
        )
        logger.color_debug(f"Drew {bird['name']} at ({x}, {y}) size ({w}, {h})")
    
    # Draw rectangles for tray
    logger.color_info("Drawing tray regions...")
    for bird in trayBirds:
        # These coordinates should match exactly what take_screenshot_region uses
        x = int(bird['rect']['x'] * img_width)
        y = int(bird['rect']['y'] * img_height)
        w = int(bird['rect']['w'] * img_width)
        h = int(bird['rect']['h'] * img_height)
        
        # Draw rectangle (left, top, right, bottom)
        draw.rectangle(
            [(x, y), (x + w, y + h)],
            outline=bird['color'],
            width=3
        )
        logger.color_debug(f"Drew {bird['name']} at ({x}, {y}) size ({w}, {h})")
    
    # Draw rectangles for EORs
    logger.color_info("Drawing EOR regions...")
    for eor in endOfRoundGoals:
        x = int(eor['rect']['x'] * img_width)
        y = int(eor['rect']['y'] * img_height)
        w = int(eor['rect']['w'] * img_width)
        h = int(eor['rect']['h'] * img_height)
        
        # Draw rectangle
        draw.rectangle(
            [(x, y), (x + w, y + h)],
            outline=eor['color'],
            width=3
        )
        logger.color_debug(f"Drew {eor['name']} at ({x}, {y}) size ({w}, {h})")
    
    # Save annotated image
    annotated_file = f"{test_dir}/annotated_window_{timestamp}.png"
    img.save(annotated_file)
    logger.color_info(f"Saved annotated screenshot: {annotated_file}")
    logger.color_info(f"Check {annotated_file} to verify all regions are correctly positioned")

def test_bird_and_eor_coordinates_with_ocr():
    """
    Take one full screenshot, draw colored rectangles around bird, tray, and EOR
    regions, and OCR each region, logging the result at SILLY level.
    """
    logger.color_info(f"Testing bird and EOR coordinates with OCR - taking screenshot in {TEST_COUNTDOWN_SECONDS} seconds")
    time.sleep(TEST_COUNTDOWN_SECONDS)

    timestamp = time.strftime('%Y%m%d_%H%M%S')
    test_dir = f"{SCREENSHOT_DIR}/coordinate_tests"
    Path(test_dir).mkdir(parents=True, exist_ok=True)

    # Capture full window
    full_window_file = f"{test_dir}/full_window_{timestamp}.png"
    cmd = f"screencapture -R{WINDOW_X_OFFSET},{WINDOW_Y_OFFSET},{WINDOW_W},{WINDOW_H} {full_window_file}"
    subprocess.run(cmd, shell=True)
    logger.color_info(f"Captured full window screenshot")

    # Load image and prepare to draw
    img = Image.open(full_window_file)
    draw = ImageDraw.Draw(img)
    img_width, img_height = img.size

    # Draw and OCR the bird regions
    logger.color_info("Drawing and OCRing bird regions...")
    starting_bird_results = {}
    for bird in startingBirds:
        x = int(bird['rect']['x'] * img_width)
        y = int(bird['rect']['y'] * img_height)
        w = int(bird['rect']['w'] * img_width)
        h = int(bird['rect']['h'] * img_height)

        draw.rectangle(
            [(x, y), (x + w, y + h)],
            outline=bird['color'],
            width=3
        )
        logger.color_debug(f"Drew {bird['name']} at ({x}, {y}) size ({w}, {h})")

        ocr_result = crop_region_and_check_ocr(img, timestamp, bird)
        starting_bird_results[bird['name']] = ocr_result
        logger.color_silly(f"OCR result for {bird['name']}: '{ocr_result}'")

    # Match starting bird OCR results to known birds
    for name, match in zip(starting_bird_results.keys(), match_bird_name_to_bird(list(starting_bird_results.values()))):
        if match['match'] is not None:
            logger.color_silly(f"Matched {name} ('{match['name']}') to '{match['match']}' (ratio: {match['ratio']:.2f})")
        else:
            logger.color_silly(f"No match found for {name} ('{match['name']}')")

    # Draw and OCR the tray regions
    logger.color_info("Drawing and OCRing tray regions...")
    tray_bird_results = {}
    for bird in trayBirds:
        x = int(bird['rect']['x'] * img_width)
        y = int(bird['rect']['y'] * img_height)
        w = int(bird['rect']['w'] * img_width)
        h = int(bird['rect']['h'] * img_height)

        draw.rectangle(
            [(x, y), (x + w, y + h)],
            outline=bird['color'],
            width=3
        )
        logger.color_debug(f"Drew {bird['name']} at ({x}, {y}) size ({w}, {h})")

        ocr_result = crop_region_and_check_ocr(img, timestamp, bird)
        tray_bird_results[bird['name']] = ocr_result
        logger.color_silly(f"OCR result for {bird['name']}: '{ocr_result}'")

    # Match tray bird OCR results to known birds
    for name, match in zip(tray_bird_results.keys(), match_bird_name_to_bird(list(tray_bird_results.values()))):
        if match['match'] is not None:
            logger.color_silly(f"Matched {name} ('{match['name']}') to '{match['match']}' (ratio: {match['ratio']:.2f})")
        else:
            logger.color_silly(f"No match found for {name} ('{match['name']}')")

    # Draw and OCR the EOR regions
    logger.color_info("Drawing and OCRing EOR regions...")
    for eor in endOfRoundGoals:
        x = int(eor['rect']['x'] * img_width)
        y = int(eor['rect']['y'] * img_height)
        w = int(eor['rect']['w'] * img_width)
        h = int(eor['rect']['h'] * img_height)

        draw.rectangle(
            [(x, y), (x + w, y + h)],
            outline=eor['color'],
            width=3
        )
        logger.color_debug(f"Drew {eor['name']} at ({x}, {y}) size ({w}, {h})")

        ocr_result = crop_region_and_check_ocr(img, timestamp, eor)
        logger.color_silly(f"OCR result for {eor['name']}: '{ocr_result}'")

    # Save annotated image
    annotated_file = f"{test_dir}/annotated_window_{timestamp}.png"
    img.save(annotated_file)
    logger.color_info(f"Saved annotated screenshot: {annotated_file}")
    logger.color_info(f"Check {annotated_file} to verify all regions are correctly positioned")

def create_coordinate_grid():
    """Create a screenshot with a coordinate grid overlay for measurement."""
    logger.color_info(f"Creating coordinate grid in {TEST_COUNTDOWN_SECONDS} seconds...")
    time.sleep(TEST_COUNTDOWN_SECONDS)
    
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    test_dir = f"{SCREENSHOT_DIR}/coordinate_tests"
    Path(test_dir).mkdir(parents=True, exist_ok=True)
    
    # Capture full window
    full_window_file = f"{test_dir}/grid_{timestamp}.png"
    cmd = f"screencapture -R{WINDOW_X_OFFSET},{WINDOW_Y_OFFSET},{WINDOW_W},{WINDOW_H} {full_window_file}"
    subprocess.run(cmd, shell=True)
    
    # Load and draw grid
    img = Image.open(full_window_file)
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    # Draw vertical lines every GRID_SPACING_PX pixels
    for x in range(0, width, GRID_SPACING_PX):
        draw.line([(x, 0), (x, height)], fill=(255, 0, 0), width=1)
        draw.text((x + 5, 5), str(x), fill=(255, 0, 0))

    # Draw horizontal lines every GRID_SPACING_PX pixels
    for y in range(0, height, GRID_SPACING_PX):
        draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=1)
        draw.text((5, y + 5), str(y), fill=(255, 0, 0))
    
    grid_file = f"{test_dir}/grid_annotated_{timestamp}.png"
    img.save(grid_file)
    logger.color_info(f"Grid saved: {grid_file}")
    logger.color_info(f"Image dimensions: {width}x{height}")

if __name__ == "__main__":
    """
    The window should be in 2560x1664 resolution, with the Wingspan window in the top left corner.
    The script will take screenshots and perform OCR to detect the End-of-Round goal or specific birds in the starting hand. It will reload the game until the desired conditions are met.
    Press Ctrl+C or enable Caps Lock to stop the automation at any time.
    """
    # test_bird_and_eor_coordinates()
    # test_bird_and_eor_coordinates_with_ocr()
    # create_coordinate_grid()
    logger.color_info("Starting in 3 seconds... Focus the Wingspan window!")
    time.sleep(3)
    reload_until_threshold_met(automa=True)
    # perform_ocr_local("screenshots/temp_region_eor2_20250930_211337.png")
    # annotate_screenshot(Image.open("screenshots/full_window_20250930_194519.png"), "20250930_194519")