"""Tests for streampanel.panel_layout."""

from __future__ import annotations

import unittest

from streampanel import panel_layout
from streampanel.window_chrome import STRIP_HEIGHT


class PanelLayoutTests(unittest.TestCase):
    def test_content_rows_empty_and_full(self) -> None:
        self.assertEqual(panel_layout.content_rows(0), 1)
        self.assertEqual(panel_layout.content_rows(1, cols=4), 1)
        self.assertEqual(panel_layout.content_rows(4, cols=4), 1)
        self.assertEqual(panel_layout.content_rows(5, cols=4), 2)

    def test_min_max_height_ordering(self) -> None:
        for n in (0, 1, 8, 9):
            lo = panel_layout.min_panel_height(n)
            hi = panel_layout.max_panel_height(n)
            self.assertLess(lo, hi)
            self.assertEqual(hi - lo, panel_layout.ROW_H)

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
        self.assertGreaterEqual(h0, STRIP_HEIGHT + panel_layout.BODY_ABOVE_GRID_H)


if __name__ == "__main__":
    unittest.main()
