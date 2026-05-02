"""Tests for streampanel.panel_layout."""

from __future__ import annotations

import unittest

from streampanel import panel_layout
from streampanel.window_chrome import STRIP_HEIGHT


class PanelLayoutTests(unittest.TestCase):
    def test_drawer_collapsed_min_height(self) -> None:
        self.assertEqual(
            panel_layout.drawer_collapsed_min_height(),
            STRIP_HEIGHT + panel_layout.DRAWER_PEEK_H,
        )

    def test_content_rows_empty_and_full(self) -> None:
        self.assertEqual(panel_layout.content_rows(0), 1)
        self.assertEqual(panel_layout.content_rows(1, cols=4), 1)
        self.assertEqual(panel_layout.content_rows(4, cols=4), 1)
        self.assertEqual(panel_layout.content_rows(5, cols=4), 2)

    def test_min_max_height_ordering(self) -> None:
        for n in (0, 1, 8, 9):
            lo = panel_layout.min_panel_height(n)
            hi = panel_layout.max_panel_height(n)
            self.assertEqual(lo, hi)

    def test_clamp_root_geometry(self) -> None:
        x, y, w, h = panel_layout.clamp_root_geometry(
            10,
            10,
            2000,
            2000,
            vroot_x=0,
            vroot_y=0,
            vroot_w=1920,
            vroot_h=1080,
            max_w=1920,
            min_w=360,
            min_h=200,
            max_h=400,
        )
        self.assertEqual(w, 1920)
        self.assertEqual(h, 400)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)
        self.assertLessEqual(x + w, 1920)
        self.assertLessEqual(y + h, 1080)

    def test_strip_included_in_heights(self) -> None:
        h0 = panel_layout.min_panel_height(0)
        self.assertGreaterEqual(h0, STRIP_HEIGHT)

    def test_min_panel_width_grows_with_items(self) -> None:
        w0 = panel_layout.min_panel_width(0, cols=4)
        w4 = panel_layout.min_panel_width(4, cols=4)
        self.assertLess(w0, w4)
        self.assertEqual(w0, panel_layout.PANEL_WIDTH_CURVE_BASE)
        self.assertEqual(
            panel_layout.min_panel_width(999, cols=4),
            panel_layout.PANEL_WIDTH_CURVE_CAP,
        )

    def test_min_panel_width_respects_many_columns(self) -> None:
        w = panel_layout.min_panel_width(0, cols=8)
        self.assertGreaterEqual(
            w,
            panel_layout.INNER_PAD_X + 8 * panel_layout.MIN_DECK_COL_WIDTH,
        )

    def test_deck_intrinsic_width_matches_strip(self) -> None:
        self.assertEqual(
            panel_layout.deck_intrinsic_width(4),
            panel_layout.INNER_PAD_X + 4 * panel_layout.MIN_DECK_COL_WIDTH,
        )

    def test_deck_intrinsic_width_scales_with_cell_px(self) -> None:
        w50 = panel_layout.deck_intrinsic_width(4, cell_px=50)
        w70 = panel_layout.deck_intrinsic_width(4, cell_px=70)
        fp50 = panel_layout.deck_column_footprint(50)
        fp70 = panel_layout.deck_column_footprint(70)
        self.assertEqual(w50, panel_layout.INNER_PAD_X + 4 * fp50)
        self.assertEqual(w70, panel_layout.INNER_PAD_X + 4 * fp70)
        self.assertLess(w50, w70)

    def test_cap_shell_width_excess_shrinks_only_when_clearly_wide(self) -> None:
        intrinsic = panel_layout.deck_intrinsic_width(4)
        min_w = panel_layout.min_panel_width(0, cols=4)
        self.assertEqual(
            panel_layout.cap_shell_width_excess(500, min_w, intrinsic),
            500,
        )
        wide = max(min_w * 2, intrinsic + 200)
        capped = panel_layout.cap_shell_width_excess(wide, min_w, intrinsic)
        self.assertEqual(capped, max(min_w, intrinsic))


if __name__ == "__main__":
    unittest.main()
