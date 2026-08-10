# Wingspan Reset Tool

Automates resetting a starting hand in Wingspan.<br/>

It repeatedly
reloads a new game, reads the text on the birds, tray and EOR and scores them against a point value you configure, either keeping good hands and continuing, or stopping once a good hand is found.

## Requirements

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed and on
  your `PATH`
- Python packages: see `requirements.txt`

The itself is cross-platform, altho I've only tested it on macOS.

## Installation

```bash
git clone <this repo>
cd wingspan_reset
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
source venv/bin/activate
python3 gui_main.py
```

### Calibration:

Everything is measured as a fraction of the Wingspan window, so it needs to
be calibrated once for your screen resolution and window position.

1. Position the Wingspan window in the top-left area of your screen and don't
   move it.
2. On the **Params** tab, under "Window Geometry", set X/Y offset to the
   window's top-left corner on screen and Width/Height to its size (for me this includes the unuseable menu bar at the top which is about 45 pixels). Save.
3. On the **Calibration** tab, click **Capture Screenshot**, focus the wingspan window during the 3 second countdown.
4. If the boxes or the button are not correctly aligned with where they are on screen, select the item from the list and redraw it on the screenshot (make text regions slightly larger)
5. Click **Test OCR on current regions** check that the text is being read.
6. **Save to Config** when the regions line up and OCR reads correctly.
   **Revert** discards unsaved changes back to the last save.

### Config:

You can configure a set amount of points for every bird/EOR, the hand will be considered valid if that point threshold is met.

For example if I say Nightingale is 1 point, Savi's Warbler is 1 point, and NO GOAL is 2 points, and I set the threshold on 3, then the hand can only be kept if NO GOAL + one of the two birds is found.

If you want to guarantee NO GOAL, set it really high.

## Other files

- `scripts/autoclicker.py` is an autoclicker, useful for the nightjar clicks (you can set a number of clicks)
- `scripts/wingspan_automation.py` is the original script, mac specific
