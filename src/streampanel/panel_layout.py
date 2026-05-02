"""Window size clamps for the panel shell (grid columns stubbed until deck-grid-ui)."""

from __future__ import annotations

from streampanel.window_chrome import STRIP_HEIGHT

# Thin row below the strip when the deck drawer is collapsed (re-open tab).
DRAWER_PEEK_H = 20


def drawer_collapsed_min_height() -> int:
    """Minimum root height with title strip + peek row (deck hidden)."""
    return int(STRIP_HEIGHT) + int(DRAWER_PEEK_H)


# Column count for deck grid and height math (see deck_grid.py).
DEFAULT_GRID_COLS = 4
# Default square deck cell (user may override via ``AppSettings.deck_cell_px``).
DEFAULT_DECK_CELL_PX = 50
DECK_CELL_PAD_X = 8
GRID_COLS_CLAMP_MIN = 2
GRID_COLS_CLAMP_MAX = 8
# Growing min-width curve: starts well below the old fixed 600px shell, caps there.
PANEL_WIDTH_CURVE_BASE = 400
PANEL_WIDTH_CURVE_CAP = 600
PANEL_WIDTH_PER_ITEM = 14
# Back-compat name: maximum auto min width (previous fixed minimum).
MIN_PANEL_WIDTH = PANEL_WIDTH_CURVE_CAP

BODY_PAD_Y = 16
# Horizontal inset of the body inner frame (``padx=20`` in app) summed.
INNER_PAD_X = 40


def deck_row_h(cell_px: int) -> int:
    """Row frame height for one deck row (cell + vertical padding model)."""
    return int(cell_px) + DECK_CELL_PAD_X


def deck_column_footprint(cell_px: int) -> int:
    """Per-column width including horizontal grid padding (``padx=4`` each side)."""
    return int(cell_px) + DECK_CELL_PAD_X


# Module-level defaults for tests / callers that omit ``cell_px``.
ROW_H = deck_row_h(DEFAULT_DECK_CELL_PX)
MIN_DECK_COL_WIDTH = deck_column_footprint(DEFAULT_DECK_CELL_PX)


def deck_strip_width(cols: int, cell_px: int = DEFAULT_DECK_CELL_PX) -> int:
    """Pixel width of the deck grid only (columns × cell footprint)."""
    c = max(GRID_COLS_CLAMP_MIN, min(GRID_COLS_CLAMP_MAX, int(cols)))
    return c * deck_column_footprint(cell_px)


def deck_intrinsic_width(cols: int, cell_px: int = DEFAULT_DECK_CELL_PX) -> int:
    """Body inner width needed for the fixed-size deck strip (pads + deck)."""
    return INNER_PAD_X + deck_strip_width(cols, cell_px)


def cap_shell_width_excess(
    w: int,
    min_w: int,
    intrinsic_deck: int,
    *,
    margin: int = 24,
) -> int:
    """
    If the shell is clearly wider than the deck needs, shrink toward intrinsic width.

    Uses two thresholds so modest manual widening is not reset on every flush.
    """
    w = max(1, int(w))
    min_w = max(1, int(min_w))
    intrinsic = max(1, int(intrinsic_deck))
    hi1 = (min_w * 135 + 99) // 100  # ceil(min_w * 1.35)
    hi2 = intrinsic + margin
    if w > hi1 and w > hi2:
        return max(min_w, intrinsic)
    return max(min_w, w)


def min_panel_width(
    item_count: int,
    cols: int = DEFAULT_GRID_COLS,
    cell_px: int = DEFAULT_DECK_CELL_PX,
) -> int:
    """Minimum shell width: narrow when the deck is small, widens as items are added."""
    c = max(GRID_COLS_CLAMP_MIN, min(GRID_COLS_CLAMP_MAX, int(cols)))
    fp = deck_column_footprint(cell_px)
    grid_floor = INNER_PAD_X + c * fp
    n = max(0, int(item_count))
    curve = min(
        PANEL_WIDTH_CURVE_CAP,
        PANEL_WIDTH_CURVE_BASE + PANEL_WIDTH_PER_ITEM * n,
    )
    return max(grid_floor, curve)


def content_rows(item_count: int, cols: int = DEFAULT_GRID_COLS) -> int:
    """Rows needed for shortcuts (at least one when the deck is empty)."""
    if item_count <= 0:
        return 1
    return (item_count + cols - 1) // cols


def min_panel_height(
    item_count: int,
    cols: int = DEFAULT_GRID_COLS,
    cell_px: int = DEFAULT_DECK_CELL_PX,
) -> int:
    """Chrome + deck rows (no footer strip below the deck)."""
    cr = content_rows(item_count, cols)
    return STRIP_HEIGHT + 2 * BODY_PAD_Y + cr * deck_row_h(cell_px)


def max_panel_height(
    item_count: int,
    cols: int = DEFAULT_GRID_COLS,
    cell_px: int = DEFAULT_DECK_CELL_PX,
) -> int:
    """Same as min height: no spare deck row (removed bottom ``+ add`` strip)."""
    return min_panel_height(item_count, cols, cell_px)


def clamp_root_geometry(
    x: int,
    y: int,
    w: int,
    h: int,
    *,
    vroot_x: int,
    vroot_y: int,
    vroot_w: int,
    vroot_h: int,
    max_w: int,
    min_w: int,
    min_h: int,
    max_h: int,
) -> tuple[int, int, int, int]:
    w = max(min_w, min(w, max_w))
    h = max(min_h, min(h, max_h))
    x = max(vroot_x, min(x, vroot_x + vroot_w - w))
    y = max(vroot_y, min(y, vroot_y + vroot_h - h))
    return x, y, w, h
