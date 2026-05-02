"""Windows-only: utility-window style (no taskbar button). Does not enable click-through."""

from __future__ import annotations

import sys
from typing import Any


def apply_tool_window_overlay(root: Any) -> None:
    """Set WS_EX_TOOLWINDOW on the Tk HWND (small overlay; not click-through)."""
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
    WS_EX_TOOLWINDOW = 0x00000080
    user32 = ctypes.windll.user32
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_TOOLWINDOW)
