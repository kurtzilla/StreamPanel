"""One main StreamPanel window per ``user_data_dir()`` (Windows mutex + HWND file; POSIX flock)."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

_INSTANCE_FILENAME = ".streampanel-instance.json"
_LOCK_FILENAME = ".streampanel.lock"
_MUTEX_PREFIX = "Local\\StreamPanel_"


def mutex_name_for_data_dir(data_dir: Path) -> str:
    """Stable Win32 mutex name derived from resolved user data path."""
    key = str(data_dir.resolve()).casefold().encode("utf-8", errors="replace")
    digest = hashlib.sha256(key).hexdigest()[:16]
    return f"{_MUTEX_PREFIX}{digest}"


def _instance_path(data_dir: Path) -> Path:
    return data_dir / _INSTANCE_FILENAME


def _try_foreground_windows_instance(data_dir: Path) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
    except ImportError:
        return
    path = _instance_path(data_dir)
    if not path.is_file():
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        hwnd = int(raw["hwnd"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return
    user32 = ctypes.windll.user32
    if not user32.IsWindow(hwnd):
        return
    SW_RESTORE = 9
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)


# Keep mutex handle alive for process lifetime (Windows).
_MUTEX_HANDLES: list[int] = []
# POSIX: hold lock fd open until exit.
_LOCK_FDS: list[int] = []


def acquire_or_exit(*, data_dir: Path) -> None:
    """
    If another StreamPanel is already running for this *data_dir*, try to foreground
    it (Windows) and ``sys.exit(0)``. Otherwise acquire the lock and return.
    """
    if sys.platform == "win32":
        _acquire_windows_or_exit(data_dir)
    else:
        _acquire_posix_or_exit(data_dir)


def _acquire_windows_or_exit(data_dir: Path) -> None:
    try:
        import ctypes
    except ImportError:
        return
    kernel32 = ctypes.windll.kernel32
    name = mutex_name_for_data_dir(data_dir)
    mutex = kernel32.CreateMutexW(None, False, name)
    if not mutex:
        return
    err = int(kernel32.GetLastError())
    ERROR_ALREADY_EXISTS = 183
    if err == ERROR_ALREADY_EXISTS:
        _try_foreground_windows_instance(data_dir)
        sys.exit(0)
    _MUTEX_HANDLES.append(int(mutex))


def _acquire_posix_or_exit(data_dir: Path) -> None:
    try:
        import fcntl
    except ImportError:
        return
    path = data_dir / _LOCK_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        try:
            os.close(fd)
        except OSError:
            pass
        sys.exit(0)
    _LOCK_FDS.append(fd)


def register_main_window_hwnd(root: Any, data_dir: Path) -> None:
    """Write HWND + pid so a second instance can foreground this window (Windows)."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(root.winfo_id())
    except Exception:
        return
    if hwnd <= 0:
        return
    payload = {"hwnd": hwnd, "pid": os.getpid()}
    try:
        _instance_path(data_dir).write_text(
            json.dumps(payload, separators=(",", ":")),
            encoding="utf-8",
        )
    except OSError:
        pass
