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
    # Full monitor rect from Win32 ``rcMonitor``; when None, layout uses work rect.
    mon_left: int | None = None
    mon_top: int | None = None
    mon_right: int | None = None
    mon_bottom: int | None = None

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)


def monitor_rect_for_layout(m: WorkMonitor) -> tuple[int, int, int, int]:
    """Bounding rect for spatial strip minimap (physical screens, not work area)."""
    if m.mon_left is None:
        return (m.left, m.top, m.right, m.bottom)
    return (m.mon_left, m.mon_top, m.mon_right, m.mon_bottom)


def _separate_normalized_centers(
    pts: list[tuple[float, float]],
    *,
    min_dist: float = 0.16,
) -> list[tuple[float, float]]:
    """Push overlapping minimap positions apart; coordinates stay in [0, 1]."""
    out = list(pts)
    n = len(out)
    if n <= 1:
        return out
    for _ in range(32):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                xi, yi = out[i]
                xj, yj = out[j]
                dx, dy = xj - xi, yj - yi
                dist_sq = dx * dx + dy * dy
                if dist_sq < 1e-12:
                    dx, dy, dist = 0.01, 0.0, 0.01
                else:
                    dist = dist_sq**0.5
                if dist >= min_dist:
                    continue
                push = (min_dist - dist) * 0.5
                if dist < 1e-9:
                    ux, uy = 1.0, 0.0
                else:
                    ux, uy = dx / dist, dy / dist
                ni = (xi - ux * push, yi - uy * push)
                nj = (xj + ux * push, yj + uy * push)
                ni = (max(0.0, min(1.0, ni[0])), max(0.0, min(1.0, ni[1])))
                nj = (max(0.0, min(1.0, nj[0])), max(0.0, min(1.0, nj[1])))
                if abs(ni[0] - out[i][0]) > 1e-6 or abs(ni[1] - out[i][1]) > 1e-6:
                    moved = True
                if abs(nj[0] - out[j][0]) > 1e-6 or abs(nj[1] - out[j][1]) > 1e-6:
                    moved = True
                out[i], out[j] = ni, nj
        if not moved:
            break
    return out


def monitor_strip_layout_centers(monitors: list[WorkMonitor]) -> list[tuple[float, float]]:
    """
    Normalized ``(relx, rely)`` in ``[0, 1]`` for each monitor, same order as *monitors*.
    Uses full monitor rects when present (see :func:`monitor_rect_for_layout`).
    """
    if not monitors:
        return []
    rects = [monitor_rect_for_layout(m) for m in monitors]
    ml = min(r[0] for r in rects)
    mt = min(r[1] for r in rects)
    mr = max(r[2] for r in rects)
    mb = max(r[3] for r in rects)
    span_w = max(1, mr - ml)
    span_h = max(1, mb - mt)
    raw: list[tuple[float, float]] = []
    for r in rects:
        cx = (r[0] + r[2]) / 2.0
        cy = (r[1] + r[3]) / 2.0
        nx = (cx - ml) / span_w
        ny = (cy - mt) / span_h
        raw.append((max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny))))
    return _separate_normalized_centers(raw)


def monitor_strip_host_wh(
    monitors: list[WorkMonitor],
    *,
    strip_inner_height: int,
) -> tuple[int, int]:
    """Pixel size for the strip minimap host; aspect follows virtual monitor span."""
    rects = [monitor_rect_for_layout(m) for m in monitors]
    span_w = max(1, max(r[2] for r in rects) - min(r[0] for r in rects))
    span_h = max(1, max(r[3] for r in rects) - min(r[1] for r in rects))
    ar = span_w / span_h
    hh = max(22, int(strip_inner_height))
    hw = int(max(44, min(120, round(hh * ar))))
    return hw, hh


def monitor_strip_spatial_ui(
    monitors: list[WorkMonitor],
    *,
    strip_inner_height: int = 26,
) -> tuple[list[tuple[float, float]], tuple[int, int]] | None:
    """
    Centers and host size for a spatial display strip, or ``None`` for a single monitor.

    ``strip_inner_height`` should match the chrome strip (e.g. ``STRIP_HEIGHT - 10``).
    """
    if len(monitors) <= 1:
        return None
    centers = monitor_strip_layout_centers(monitors)
    wh = monitor_strip_host_wh(monitors, strip_inner_height=strip_inner_height)
    return centers, wh


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
        rw = mi.rcWork
        rm = mi.rcMonitor
        primary = bool(mi.dwFlags & MONITORINFOF_PRIMARY)
        collected.append(
            WorkMonitor(
                int(rw.left),
                int(rw.top),
                int(rw.right),
                int(rw.bottom),
                is_primary=primary,
                mon_left=int(rm.left),
                mon_top=int(rm.top),
                mon_right=int(rm.right),
                mon_bottom=int(rm.bottom),
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
