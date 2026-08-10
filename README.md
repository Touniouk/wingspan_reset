# Wingspan Automation

Automates "mulligan-ing" a starting hand in Wingspan (macOS only). It repeatedly reloads
a new game, OCRs the End-of-Round (EOR) goal and the birds in your hand/tray, scores
them against a point system you define, and stops once a target score is reached —
either keeping the hand for you to play, or pausing with a sound alert.

## Requirements

- macOS (uses `screencapture`, `afplay`, and Quartz for Caps Lock detection — this
  will not run on Windows/Linux as-is)
- Python 3
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract): `brew install tesseract`
- Python packages: `pyautogui`, `pillow`, `pynput` (only needed for `scripts/autoclicker.py`)

```bash
python3 -m venv venv
source venv/bin/activate
pip install pyautogui pillow pynput
```

## Project layout

- `scripts/wingspan_automation.py` — the original standalone automation script
  (see below for setup/usage)
- `scripts/autoclicker.py` — small Tkinter autoclicker tuned for Wingspan's
  repeated-click screens (default 142 clicks at 2/sec); run directly with
  `python3 scripts/autoclicker.py`
- `wingspan_gui/`, `main.py`, `gui_main.py` — a Tkinter GUI port of the same
  automation logic (`python3 gui_main.py` to launch)
- `logger.py`, `birds.json` — shared by both the script and the GUI, kept at
  the repo root

## Files you need

- `scripts/wingspan_automation.py` — the script itself
- `logger.py` — small colored logger used for console/file output
- `birds.json` — Wingspan bird database, used to fuzzy-match OCR'd bird names to
  real bird common names

`logger.py` and `birds.json` must stay at the repo root; the script must be run
from the repo root (see below) so it can find them.

## macOS permissions

The first time you run this, macOS will prompt for:

- **Screen Recording** access (for `screencapture` and reading pixels)
- **Accessibility** access (for `pyautogui` to move/click the mouse)

Grant both to your terminal app (Terminal, iTerm, VS Code, etc.) in
System Settings → Privacy & Security, or the script will silently fail to click
or capture anything.

## One-time setup: calibrating your window

Everything is measured as a fraction of the Wingspan window, so it needs to be
calibrated once for your screen resolution and window position.

1. Position the Wingspan window in the top-left area of your screen and don't move it.
2. In `scripts/wingspan_automation.py`, set `WINDOW_X_OFFSET` / `WINDOW_Y_OFFSET` to the
   window's top-left corner on screen, and `WINDOW_W` / `WINDOW_H` to its width/height.
3. Use the built-in calibration helpers (uncomment the one you want in the
   `if __name__ == "__main__":` block at the bottom of the file, then run
   `python3 scripts/wingspan_automation.py` from the repo root):
   - `create_coordinate_grid()` — takes a screenshot with a pixel-coordinate grid
     overlay so you can read off `x, y` values by eye.
   - `test_bird_and_eor_coordinates()` — draws colored boxes over the configured
     bird/tray/EOR regions on a real screenshot, so you can visually confirm they
     line up with the actual card text.
   - `test_bird_and_eor_coordinates_with_ocr()` — same as above, but also runs OCR
     on every region and logs the recognized text (and matched bird name), so you
     can confirm OCR is actually reading the right thing.

   Output goes to `screenshots/coordinate_tests/`.
4. Adjust the `x`/`y`/`w`/`h` values (given as fractions of `WINDOW_W`/`WINDOW_H`)
   in `startingBirds`, `trayBirds`, and `endOfRoundGoals` until the boxes line up.
5. Adjust the click coordinates in `buttons` the same way if menu positions differ
   on your screen — click through the game manually once and note the pixel
   coordinates, then convert to fractions of `WINDOW_W`/`WINDOW_H`.

## Configuring what to look for

- **`birdPoints`** — dict of `"Bird Common Name": points`. Any of these birds found
  in your hand or tray add their point value to the score (duplicates count each
  time they appear).
- **`NO_GOAL_POINTS`** — points awarded if the "NO GOAL" End-of-Round goal is detected.
- **`POINT_THRESHOLD`** — total score (birds + EOR) needed to stop reloading and keep
  the hand.

Other tunable constants near the top of the file:

| Constant | Purpose |
|---|---|
| `SCREENSHOTS_TO_KEEP` | how many past screenshot sets to keep on disk |
| `BIRD_MATCH_MINIMUM_RATIO` | fuzzy-match confidence cutoff for OCR'd bird names |
| `WINDOW_READY_DELAY` | seconds to wait before capturing, so the window can settle |
| `TEST_COUNTDOWN_SECONDS` | countdown before the calibration helpers take a screenshot |
| `GRID_SPACING_PX` | pixel spacing between lines in `create_coordinate_grid` |
| `ALERT_SOUND_PATH` | sound file played when the automation stops on a match |
| `LOG_FILE` | path to the log file |

## Running it

Once calibrated, edit the `if __name__ == "__main__":` block to call:

```python
reload_until_threshold_met(automa=True)
```

- `automa=True` reloads into a solo game against the Automa bot; `automa=False`
  reloads into a standard custom game.
- `continue_on_match=True` (default): once the point threshold is met, it selects
  the hand and keeps reloading anyway (useful for just logging what a good hand
  looks like). Set `continue_on_match=False` to actually stop the automation and
  play an alert sound when a good hand is found.

Then:

```bash
source venv/bin/activate
python3 scripts/wingspan_automation.py
```

Run this from the repo root — the script looks for `birds.json` and writes to
`screenshots/` relative to the current directory.

Focus the Wingspan window during the 3-second startup countdown. **Press Ctrl+C or
turn on Caps Lock at any time to stop the automation immediately.**

## Troubleshooting

- **Nothing gets clicked / no screenshots appear**: check macOS Screen Recording
  and Accessibility permissions (see above).
- **OCR results look like garbage**: re-run `test_bird_and_eor_coordinates_with_ocr()`
  to see exactly what's being cropped and read; your region coordinates or window
  offsets are probably off.
- **"No bird names were matched successfully"**: usually means the screenshot was
  taken before the game screen finished rendering — try increasing
  `WINDOW_READY_DELAY` or the relevant button's `delay` in `buttons`.
