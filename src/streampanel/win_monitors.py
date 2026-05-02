"""Windows: enumerate display work areas for per-monitor clamping and top-rail drag."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkMonitor:
    """Desktop work area (excludes taskbar) in virtual-screen coordinates."""

    left: int
    top: int
    right: int
    bottom: int
    is_primary: bool = False

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)


def _sort_monitors(monitors: list[WorkMonitor]) -> list[WorkMonitor]:
    prim = [m for m in monitors if m.is_primary]
    rest = sorted((m for m in monitors if not m.is_primary), key=lambda m: (m.left, m.top))
    out = prim + rest
    if not out:
        return sorted(monitors, key=lambda m: (m.left, m.top))
    return out


def virtual_desktop_span(monitors: list[WorkMonitor]) -> tuple[int, int, int, int]:
    """Bounding box of all work areas: min_left, min_top, max_right, max_bottom."""
    if not monitors:
        return 0, 0, 1920, 1080
    ml = min(m.left for m in monitors)
    mt = min(m.top for m in monitors)
    mr = max(m.right for m in monitors)
    mb = max(m.bottom for m in monitors)
    return ml, mt, mr, mb


def list_work_monitors(root: Any | None = None) -> list[WorkMonitor]:
    """Enumerate monitors; on non-Windows or failure, fall back to Tk vroot or a default."""
    if sys.platform == "win32":
        try:
            mons = _list_work_monitors_win32()
            if mons:
                return _sort_monitors(mons)
        except Exception:
            pass
    if root is not None:
        try:
            vx = int(root.winfo_vrootx())
            vy = int(root.winfo_vrooty())
            vw = int(root.winfo_vrootwidth())
            vh = int(root.winfo_vrootheight())
            return [
                WorkMonitor(vx, vy, vx + vw, vy + vh, is_primary=True),
            ]
        except Exception:
            pass
    return [WorkMonitor(0, 0, 1920, 1080, is_primary=True)]


def monitor_for_point_x(px: int, monitors: list[WorkMonitor]) -> WorkMonitor:
    """Pick the work area whose horizontal span contains *px* (virtual x)."""
    if not monitors:
        return WorkMonitor(0, 0, 1920, 1080, is_primary=True)
    for m in monitors:
        if m.left <= px < m.right:
            return m
    return min(monitors, key=lambda m: abs(px - (m.left + m.right) // 2))


def monitor_for_panel_center(
    x: int, y: int, w: int, h: int, monitors: list[WorkMonitor]
) -> WorkMonitor:
    cx = x + max(1, w) // 2
    cy = y + max(1, h) // 2
    for m in monitors:
        if m.left <= cx < m.right and m.top <= cy < m.bottom:
            return m
    return monitor_for_point_x(cx, monitors)


def snap_top_rail(
    x: int,
    _y: int,
    w: int,
    _h: int,
    monitors: list[WorkMonitor],
    *,
    pointer_x: int,
) -> tuple[int, int]:
    """Keep the window on the top work edge of the monitor under *pointer_x*; clamp *x*."""
    m = monitor_for_point_x(pointer_x, monitors)
    nx = max(m.left, min(x, m.right - w))
    return nx, m.top


def sanitize_restored_shell_width(w: int, virtual_span_w: int, min_w: int) -> int:
    """Shrink absurd persisted widths (e.g. full virtual desktop)."""
    w = max(1, int(w))
    min_w = max(1, int(min_w))
    if virtual_span_w > 0 and w >= int(virtual_span_w * 0.88):
        return min_w
    return max(min_w, w)


def top_center_x(mon: WorkMonitor, w: int) -> int:
    """Left ``x`` so a window of width *w* is horizontally centered on monitor *mon*."""
    w = max(1, int(w))
    return mon.left + max(0, (mon.width - w) // 2)


def parse_display_choice(choice: str, n_monitors: int) -> int | None:
    """
    Map a strip picker value to a 0-based monitor index.

    Accepts ``Display N`` (case-insensitive) or a plain digit string ``N``.
    """
    if n_monitors <= 0:
        return None
    s = str(choice).strip()
    m = re.fullmatch(r"(?i)display\s+(\d+)", s)
    if m:
        idx = int(m.group(1)) - 1
        return idx if 0 <= idx < n_monitors else None
    m2 = re.fullmatch(r"(\d+)", s)
    if m2:
        idx = int(m2.group(1)) - 1
        return idx if 0 <= idx < n_monitors else None
    return None


def primary_or_first(monitors: list[WorkMonitor]) -> WorkMonitor:
    for m in monitors:
        if m.is_primary:
            return m
    return monitors[0]


def _list_work_monitors_win32() -> list[WorkMonitor]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    MONITORINFOF_PRIMARY = 1
    collected: list[WorkMonitor] = []

    def _cb(
        h_monitor: wintypes.HMONITOR,
        _hdc: wintypes.HDC,
        _lprc: ctypes.POINTER(RECT),
        _lparam: wintypes.LPARAM,
    ) -> wintypes.BOOL:
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(h_monitor, ctypes.byref(mi)):
            return True
        r = mi.rcWork
        primary = bool(mi.dwFlags & MONITORINFOF_PRIMARY)
        collected.append(
            WorkMonitor(
                int(r.left),
                int(r.top),
                int(r.right),
                int(r.bottom),
                is_primary=primary,
            )
        )
        return True

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(RECT),
        wintypes.LPARAM,
    )
    cb = MonitorEnumProc(_cb)
    if not user32.EnumDisplayMonitors(None, None, cb, 0):
        return []
    return collected
