from typing import Tuple, List
from PIL import ImageGrab
import numpy as np
import key_position as kp
import time
import pytesseract
import utils
import logger
import os_fun as os
pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/bin/tesseract'

def window_size() -> Tuple[int, int]:
    return [1365, 1023]

def window_bbox() -> Tuple[int, int, int, int]:
    upperMargin = 57
    return [0, 0+upperMargin, window_size()[0], window_size()[1]+upperMargin]

def bird_bbox() -> List[Tuple[int, int, int, int, int]]:
    return [[int(0.140 * window_size()[0]), int(0.313 * window_size()[1]), int(0.246 * window_size()[0]), int(0.355 * window_size()[1]), 1], 
            [int(0.304 * window_size()[0]), int(0.325 * window_size()[1]), int(0.406 * window_size()[0]), int(0.355 * window_size()[1]), 1], 
            [int(0.467 * window_size()[0]), int(0.327 * window_size()[1]), int(0.566 * window_size()[0]), int(0.362 * window_size()[1]), 0], 
            [int(0.623 * window_size()[0]), int(0.325 * window_size()[1]), int(0.724 * window_size()[0]), int(0.357 * window_size()[1]), 359], 
            [int(0.782 * window_size()[0]), int(0.319 * window_size()[1]), int(0.893 * window_size()[0]), int(0.350 * window_size()[1]), 358]]

def text_from_card(bird: Tuple[int, int, int, int, int]) -> str:
    image = ImageGrab.grab(bbox=[bird[0], bird[1], bird[2], bird[3]]).rotate(bird[4])
    logger.trace(image)
    custom_config = r"--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    imageText = pytesseract.image_to_string(image, config=custom_config).strip()
    logger.debug("image text: " + imageText)
    bird_name = min(bird_names, 
                key=lambda s: utils.minimum_edit_distance(
                    s.replace(' ', '').replace('-', '').replace('\'', '').upper(), 
                    imageText.replace(' ', '')))
    logger.trace(bird_name)
    return bird_name

if __name__ == '__main__':
    # Sleep so I have time to switch window
    time.sleep(1)
    # Grab screen
    currentScreen = ImageGrab.grab(bbox=window_bbox())
    logger.infime(currentScreen)

    # Get all bird names
    bird_names = []
    folder = 'resources/bird_names'
    with open((folder + '/base.txt'), 'r') as file:
        bird_names += file.read().splitlines()
    with open((folder + '/ee.txt'), 'r') as file:
        bird_names += file.read().splitlines()
    with open((folder + '/ss.txt'), 'r') as file:
        bird_names += file.read().splitlines()
    [item.strip().replace(' ', '').replace('-', '').replace('\'', '').replace('\n', '').upper() for item in bird_names]

    # Get the bird names from starting hand
    bird_names = [text_from_card(bird) for bird in bird_bbox()]
    logger.info("Starting hand: " + bird_names[0] + " | " + bird_names[1] + " | " + bird_names[2] + " | " + bird_names[3] + " | " + bird_names[4])

    # Check if it corresponds to any expected starting hand
    

    os.notify("Winghands", "Done")


    