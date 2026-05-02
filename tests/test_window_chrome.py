"""Tests for streampanel.window_chrome helpers (no live Tk window required)."""

from __future__ import annotations

import unittest

from streampanel import win_monitors
from streampanel.window_chrome import (
    PANEL_DRAG_ANIM_FADE,
    PANEL_DRAG_ANIM_NONE,
    PANEL_DRAG_ANIM_SLIDE,
    _resolve_anim_style,
    compute_drag_rect,
)


class ResolveAnimStyleTests(unittest.TestCase):
    def test_missing_callable(self) -> None:
        self.assertEqual(_resolve_anim_style(None), PANEL_DRAG_ANIM_NONE)

    def test_valid_strings(self) -> None:
        self.assertEqual(_resolve_anim_style(lambda: "fade"), PANEL_DRAG_ANIM_FADE)
        self.assertEqual(_resolve_anim_style(lambda: "SLIDE"), PANEL_DRAG_ANIM_SLIDE)
        self.assertEqual(_resolve_anim_style(lambda: " none "), PANEL_DRAG_ANIM_NONE)

    def test_unknown_falls_back(self) -> None:
        self.assertEqual(_resolve_anim_style(lambda: "spin"), PANEL_DRAG_ANIM_NONE)

    def test_callable_raises_falls_back(self) -> None:
        def boom() -> str:
            raise RuntimeError("x")

        self.assertEqual(_resolve_anim_style(boom), PANEL_DRAG_ANIM_NONE)


class ComputeDragRectTests(unittest.TestCase):
    def test_without_snap(self) -> None:
        w, h, x, y = compute_drag_rect(
            (10, 20),
            (300, 400),
            110,
            220,
            pointer_x=50,
            top_rail_snap=None,
        )
        self.assertEqual((w, h, x, y), (300, 400, 100, 200))

    def test_with_snap_top_rail(self) -> None:
        m1 = win_monitors.WorkMonitor(0, 10, 800, 610, is_primary=True)
        m2 = win_monitors.WorkMonitor(800, 20, 1600, 620, is_primary=False)
        mons = [m1, m2]

        def snap(px: int, x: int, y: int, w: int, h: int) -> tuple[int, int]:
            return win_monitors.snap_top_rail(x, y, w, h, mons, pointer_x=px)

        # Match win_monitors.snap_top_rail case: raw x=99 clamps to 800 on m2.
        w, h, x, y = compute_drag_rect(
            (50, 30),
            (200, 100),
            149,
            500,
            pointer_x=900,
            top_rail_snap=snap,
        )
        self.assertEqual((w, h), (200, 100))
        self.assertEqual(y, 20)
        self.assertEqual(x, 800)


class PanelDragLifecycleStubTests(unittest.TestCase):
    """Mirror app.on_panel_drag_start / on_panel_drag_end min-max pin semantics."""

    def test_pin_and_restore_minsize_maxsize(self) -> None:
        class FakeRoot:
            def __init__(self) -> None:
                self._min = (400, 280)
                self._max = (1920, 1080)
                self.minsize_calls: list[tuple[int, ...]] = []
                self.maxsize_calls: list[tuple[int, ...]] = []

            def update_idletasks(self) -> None:
                pass

            def winfo_width(self) -> int:
                return 420

            def winfo_height(self) -> int:
                return 300

            def minsize(self, *a: int) -> tuple[int, int]:
                if a:
                    self._min = (int(a[0]), int(a[1]))
                    self.minsize_calls.append((int(a[0]), int(a[1])))
                return self._min

            def maxsize(self, *a: int) -> tuple[int, int]:
                if a:
                    self._max = (int(a[0]), int(a[1]))
                    self.maxsize_calls.append((int(a[0]), int(a[1])))
                return self._max

        root = FakeRoot()
        saved: list[tuple[tuple[int, int], tuple[int, int]] | None] = [None]
        drag_active = [False]

        def on_start() -> None:
            drag_active[0] = True
            root.update_idletasks()
            w0, h0 = int(root.winfo_width()), int(root.winfo_height())
            saved[0] = (root.minsize(), root.maxsize())
            root.minsize(w0, h0)
            root.maxsize(w0, h0)

        def on_end() -> None:
            drag_active[0] = False
            s = saved[0]
            saved[0] = None
            if s is not None:
                mn, mx = s
                root.minsize(int(mn[0]), int(mn[1]))
                root.maxsize(int(mx[0]), int(mx[1]))

        on_start()
        self.assertEqual(root.minsize_calls[-1], (420, 300))
        self.assertEqual(root.maxsize_calls[-1], (420, 300))
        on_end()
        self.assertEqual(root.minsize_calls[-1], (400, 280))
        self.assertEqual(root.maxsize_calls[-1], (1920, 1080))


if __name__ == "__main__":
    unittest.main()
