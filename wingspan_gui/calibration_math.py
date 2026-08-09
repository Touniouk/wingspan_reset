"""Pure coordinate conversion between canvas pixels (what you see/drag in the
calibration tab) and the fractional x/y/w/h used everywhere else in the app.

Kept dependency-free (no Tkinter/PIL imports) so it's easy to unit test on its own.
Fractions are always relative to the captured screenshot's pixel dimensions
(img_w/img_h) - the same convention ocr.crop_region_and_check_ocr already uses -
NOT the window's point dimensions, since a screenshot may be DPI-scaled relative
to the window's logical size.
"""


def canvas_rect_to_fraction(x0: float, y0: float, x1: float, y1: float,
                             display_scale: float, img_w: int, img_h: int) -> dict:
    """Convert a canvas-pixel rectangle (as drawn/dragged) into fractional x/y/w/h."""
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))

    orig_x0 = x0 / display_scale
    orig_y0 = y0 / display_scale
    orig_x1 = x1 / display_scale
    orig_y1 = y1 / display_scale

    return {
        "x": orig_x0 / img_w,
        "y": orig_y0 / img_h,
        "w": (orig_x1 - orig_x0) / img_w,
        "h": (orig_y1 - orig_y0) / img_h,
    }


def fraction_rect_to_canvas(x: float, y: float, w: float, h: float,
                             display_scale: float, img_w: int, img_h: int) -> tuple[float, float, float, float]:
    """Inverse of canvas_rect_to_fraction - used to draw an existing region on load."""
    x0 = x * img_w * display_scale
    y0 = y * img_h * display_scale
    x1 = x0 + w * img_w * display_scale
    y1 = y0 + h * img_h * display_scale
    return x0, y0, x1, y1


def canvas_point_to_fraction(x: float, y: float, display_scale: float,
                              img_w: int, img_h: int) -> tuple[float, float]:
    """Convert a single canvas-pixel click point into fractional x/y."""
    return (x / display_scale) / img_w, (y / display_scale) / img_h


def fraction_point_to_canvas(xr: float, yr: float, display_scale: float,
                              img_w: int, img_h: int) -> tuple[float, float]:
    """Inverse of canvas_point_to_fraction - used to draw an existing button point on load."""
    return xr * img_w * display_scale, yr * img_h * display_scale


def compute_display_scale(img_w: int, img_h: int, max_w: int, max_h: int) -> float:
    """Scale factor to fit an img_w x img_h image inside max_w x max_h, never upscaling."""
    return min(max_w / img_w, max_h / img_h, 1.0)
