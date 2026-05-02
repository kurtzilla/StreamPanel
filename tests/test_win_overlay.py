"""Tests for streampanel.win_overlay (pure toggle math)."""

from __future__ import annotations

import unittest

from streampanel import win_overlay


class WinOverlayTests(unittest.TestCase):
    def test_tool_window_exstyle_toggle(self) -> None:
        ex = 0x100
        on = win_overlay.tool_window_exstyle_after_toggle(ex, excluded=True)
        self.assertEqual(on & 0x80, 0x80)
        off = win_overlay.tool_window_exstyle_after_toggle(on, excluded=False)
        self.assertEqual(off & 0x80, 0)
        self.assertEqual(off, ex)


if __name__ == "__main__":
    unittest.main()
