"""Windows-only: utility-window style (no taskbar when unfocused). Does not enable click-through."""

from __future__ import annotations

import sys
from typing import Any

_WS_EX_TOOLWINDOW = 0x00000080


def tool_window_exstyle_after_toggle(ex: int, *, excluded: bool) -> int:
    """Pure helper: extended style after applying or clearing ``WS_EX_TOOLWINDOW``."""
    if excluded:
        return int(ex) | _WS_EX_TOOLWINDOW
    return int(ex) & ~_WS_EX_TOOLWINDOW


def set_tool_window_excluded(root: Any, excluded: bool) -> None:
    """
    When *excluded* is True, set ``WS_EX_TOOLWINDOW`` (no taskbar button).
    When False, clear it so the shell can show a normal taskbar entry while the window is active.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
    except ImportError:
        return
    try:
        hwnd = int(root.winfo_id())
    except Exception:
        return
    if hwnd <= 0:
        return
    GWL_EXSTYLE = -20
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOZORDER = 0x0004
    SWP_FRAMECHANGED = 0x0020
    user32 = ctypes.windll.user32
    ex = int(user32.GetWindowLongW(hwnd, GWL_EXSTYLE))
    new_ex = tool_window_exstyle_after_toggle(ex, excluded=excluded)
    if new_ex == ex:
        return
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_ex)
    user32.SetWindowPos(
        hwnd,
        0,
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
    )


def apply_tool_window_overlay(root: Any) -> None:
    """Initial overlay: no taskbar until the user focuses the panel (see ``FocusIn`` in app)."""
    set_tool_window_excluded(root, True)


# Windows 11+: DwmSetWindowAttribute(DWMWA_WINDOW_CORNER_PREFERENCE, …)
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWCP_ROUNDSMALL = 3


def apply_dwm_rounded_corners(root: Any) -> None:
    """
    Ask the compositor for rounded window corners (Windows 11+).

    No-op on other platforms or if the attribute is unsupported. Borderless
    panels still benefit from matching in-client rounding in ``window_chrome``.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return
    try:
        hwnd = int(root.winfo_id())
    except Exception:
        return
    if hwnd <= 0:
        return
    pref = ctypes.c_int(_DWMWCP_ROUNDSMALL)
    try:
        hr = int(
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                ctypes.c_uint(_DWMWA_WINDOW_CORNER_PREFERENCE),
                ctypes.byref(pref),
                ctypes.sizeof(pref),
            )
        )
    except Exception:
        return
    if hr != 0:
        return
