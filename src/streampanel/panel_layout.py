"""Window size clamps for the panel shell (grid columns stubbed until deck-grid-ui)."""

from __future__ import annotations

from streampanel.window_chrome import STRIP_HEIGHT

# Column count for deck grid and height math (see deck_grid.py).
DEFAULT_GRID_COLS = 4
ROW_H = 56
BODY_PAD_Y = 16
# Status summary above the deck grid.
BODY_ABOVE_GRID_H = 100
MIN_PANEL_WIDTH = 600


def content_rows(item_count: int, cols: int = DEFAULT_GRID_COLS) -> int:
    """Rows needed for shortcuts (at least one when the deck is empty)."""
    if item_count <= 0:
        return 1
    return (item_count + cols - 1) // cols


def min_panel_height(item_count: int, cols: int = DEFAULT_GRID_COLS) -> int:
    """Chrome + status + filled rows (no extra blank row)."""
    cr = content_rows(item_count, cols)
    return STRIP_HEIGHT + 2 * BODY_PAD_Y + BODY_ABOVE_GRID_H + cr * ROW_H


def max_panel_height(item_count: int, cols: int = DEFAULT_GRID_COLS) -> int:
    """At most one extra blank row beyond filled rows."""
    cr = content_rows(item_count, cols)
    return (
        STRIP_HEIGHT
        + 2 * BODY_PAD_Y
        + BODY_ABOVE_GRID_H
        + (cr + 1) * ROW_H
    )


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
