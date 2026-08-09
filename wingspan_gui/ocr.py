"""Tesseract OCR helpers: cropping named regions out of a screenshot and reading their text."""

import subprocess
from pathlib import Path

from wingspan_gui.config import SCREENSHOT_DIR


def perform_ocr_local(filename: str, logger) -> str:
    """
    Use tesseract (local OCR) to extract text from an image.

    Returns:
        str: Normalized OCR result (uppercase, whitespace-collapsed) or "Nothing" on failure
    """
    logger.color_debug("Performing OCR with tesseract for file: " + filename)

    try:
        result = subprocess.run(
            ['tesseract', filename, 'stdout',
             '--psm', '6',  # Uniform block of text
             '--oem', '3',  # Use LSTM neural net (most accurate)
             '-c', 'tessedit_char_blacklist=0123456789!@#$%^&*()'
             ],
            capture_output=True,
            text=True,
            check=True
        )
        normalized = ' '.join(result.stdout.split()).upper()
        logger.color_debug(f"OCR result: '{normalized}'")
        return normalized
    except subprocess.CalledProcessError as e:
        logger.color_error(f"OCR failed: {e}")
        return "Nothing"


def crop_region_and_check_ocr(full_img, timestamp: str, region, logger, delete_temp_file: bool = True) -> str:
    """
    Crop a named region (fractional x/y/w/h relative to full_img's pixel size)
    out of the full screenshot and OCR it.
    """
    img_width, img_height = full_img.size

    x = int(region.x * img_width)
    y = int(region.y * img_height)
    w = int(region.w * img_width)
    h = int(region.h * img_height)

    region_crop = full_img.crop((x, y, x + w, y + h))
    region_crop_file = f"{SCREENSHOT_DIR}/temp_region_{region.name}_{timestamp}.png"
    region_crop.save(region_crop_file)

    region_result = perform_ocr_local(region_crop_file, logger)

    if delete_temp_file:
        Path(region_crop_file).unlink(missing_ok=True)

    return region_result
