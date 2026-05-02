"""Tests for streampanel.win_monitors (pure helpers; no live Win32 required)."""

from __future__ import annotations

import unittest

from streampanel import win_monitors


class ParseDisplayChoiceTests(unittest.TestCase):
    def test_display_label(self) -> None:
        self.assertEqual(win_monitors.parse_display_choice("Display 1", 2), 0)
        self.assertEqual(win_monitors.parse_display_choice("display 2", 2), 1)

    def test_plain_digit(self) -> None:
        self.assertEqual(win_monitors.parse_display_choice("1", 3), 0)
        self.assertEqual(win_monitors.parse_display_choice("  3  ", 3), 2)

    def test_out_of_range_or_invalid(self) -> None:
        self.assertIsNone(win_monitors.parse_display_choice("Display 9", 2))
        self.assertIsNone(win_monitors.parse_display_choice("Display 0", 2))
        self.assertIsNone(win_monitors.parse_display_choice("x", 2))
        self.assertIsNone(win_monitors.parse_display_choice("1", 0))


class WinMonitorsTests(unittest.TestCase):
    def test_top_center_x(self) -> None:
        m = win_monitors.WorkMonitor(100, 0, 900, 600, is_primary=True)
        self.assertEqual(win_monitors.top_center_x(m, 400), 300)
        self.assertEqual(win_monitors.top_center_x(m, 900), 100)

    def test_sanitize_restored_shell_width(self) -> None:
        self.assertEqual(
            win_monitors.sanitize_restored_shell_width(3000, 3200, 400),
            400,
        )
        self.assertEqual(
            win_monitors.sanitize_restored_shell_width(500, 3200, 400),
            500,
        )

    def test_snap_top_rail(self) -> None:
        m1 = win_monitors.WorkMonitor(0, 10, 800, 610, is_primary=True)
        m2 = win_monitors.WorkMonitor(800, 20, 1600, 620, is_primary=False)
        mons = [m1, m2]
        x, y = win_monitors.snap_top_rail(50, 99, 200, 100, mons, pointer_x=100)
        self.assertEqual(y, 10)
        self.assertEqual(x, 50)
        x2, y2 = win_monitors.snap_top_rail(750, 99, 200, 100, mons, pointer_x=900)
        self.assertEqual(y2, 20)
        self.assertEqual(x2, 800)
        self.assertLessEqual(x2 + 200, 1600)

    def test_monitor_for_point_x_gap(self) -> None:
        m1 = win_monitors.WorkMonitor(0, 0, 100, 100, True)
        m2 = win_monitors.WorkMonitor(200, 0, 300, 100, False)
        picked = win_monitors.monitor_for_point_x(150, [m1, m2])
        self.assertIn(picked, (m1, m2))

    def test_virtual_desktop_span(self) -> None:
        m1 = win_monitors.WorkMonitor(0, 0, 100, 50, True)
        m2 = win_monitors.WorkMonitor(100, 10, 250, 60, False)
        ml, mt, mr, mb = win_monitors.virtual_desktop_span([m1, m2])
        self.assertEqual((ml, mt, mr, mb), (0, 0, 250, 60))


class MonitorStripLayoutTests(unittest.TestCase):
    def test_monitor_rect_for_layout_falls_back_to_work(self) -> None:
        m = win_monitors.WorkMonitor(10, 20, 110, 220, is_primary=True)
        self.assertEqual(win_monitors.monitor_rect_for_layout(m), (10, 20, 110, 220))

    def test_monitor_rect_for_layout_uses_mon_rect(self) -> None:
        m = win_monitors.WorkMonitor(
            40,
            40,
            1040,
            640,
            is_primary=True,
            mon_left=0,
            mon_top=0,
            mon_right=1080,
            mon_bottom=720,
        )
        self.assertEqual(win_monitors.monitor_rect_for_layout(m), (0, 0, 1080, 720))

    def test_layout_centers_two_horizontal(self) -> None:
        m1 = win_monitors.WorkMonitor(0, 0, 800, 600, is_primary=True)
        m2 = win_monitors.WorkMonitor(800, 0, 1600, 600, is_primary=False)
        pts = win_monitors.monitor_strip_layout_centers([m1, m2])
        self.assertEqual(len(pts), 2)
        self.assertAlmostEqual(pts[0][0], 0.25, places=2)
        self.assertAlmostEqual(pts[0][1], 0.5, places=2)
        self.assertAlmostEqual(pts[1][0], 0.75, places=2)
        self.assertAlmostEqual(pts[1][1], 0.5, places=2)

    def test_layout_centers_two_vertical(self) -> None:
        m1 = win_monitors.WorkMonitor(0, 0, 1920, 1080, is_primary=True)
        m2 = win_monitors.WorkMonitor(0, 1080, 1920, 2160, is_primary=False)
        pts = win_monitors.monitor_strip_layout_centers([m1, m2])
        self.assertEqual(len(pts), 2)
        self.assertAlmostEqual(pts[0][0], 0.5, places=2)
        self.assertAlmostEqual(pts[0][1], 0.25, places=2)
        self.assertAlmostEqual(pts[1][0], 0.5, places=2)
        self.assertAlmostEqual(pts[1][1], 0.75, places=2)

    def test_strip_spatial_ui_none_for_single(self) -> None:
        m = win_monitors.WorkMonitor(0, 0, 800, 600, is_primary=True)
        self.assertIsNone(win_monitors.monitor_strip_spatial_ui([m]))

    def test_strip_spatial_ui_returns_centers_and_host(self) -> None:
        m1 = win_monitors.WorkMonitor(0, 0, 800, 600, is_primary=True)
        m2 = win_monitors.WorkMonitor(800, 0, 1600, 600, is_primary=False)
        out = win_monitors.monitor_strip_spatial_ui([m1, m2], strip_inner_height=26)
        self.assertIsNotNone(out)
        centers, (hw, hh) = out
        self.assertEqual(len(centers), 2)
        self.assertGreater(hw, hh)


if __name__ == "__main__":
    unittest.main()
