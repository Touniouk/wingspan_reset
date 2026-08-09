"""Fuzzy-matches OCR'd bird names against the known bird list in birds.json."""

import json
import unicodedata
from difflib import SequenceMatcher

from wingspan_gui.config import BIRD_JSON


def remove_accents(text: str) -> str:
    """Remove accents/diacritics from Unicode text."""
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')


def match_bird_name_to_bird(bird_names: list[str], minimum_ratio: float, logger) -> list[dict]:
    """
    Match a list of OCR'd bird names to known bird common names from BIRD_JSON
    using fuzzy string matching.
    """
    birds = []

    with open(BIRD_JSON, 'r', encoding='utf-8') as file:
        data = json.load(file)
        candidates = [(bird['Common name'], remove_accents(bird['Common name'].upper()))
                      for bird in data]

        for name in bird_names:
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
                birds.append({'name': name, 'match': None, 'ratio': 0, 'error': 'NO_MATCH_FOUND'})
            elif best_ratio < minimum_ratio:
                logger.color_warn(f"LOW CONFIDENCE: Bird name '{name}' matched to '{best_original}' with ratio {best_ratio:.2f}")
                birds.append({'name': name, 'match': best_original, 'ratio': best_ratio, 'error': 'LOW_CONFIDENCE'})
            else:
                logger.color_silly(f"Matched '{name}' to '{best_original}' (confidence: {best_ratio:.2f})")
                birds.append({'name': name, 'match': best_original, 'ratio': best_ratio, 'error': None})

    return birds
