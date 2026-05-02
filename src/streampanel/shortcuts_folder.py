"""Resolve StreamPanel user data and shortcuts directory paths (Windows-first)."""

from __future__ import annotations

import os
from pathlib import Path

_APP_NAME = "StreamPanel"


def user_data_dir() -> Path:
    """%APPDATA%/StreamPanel (created). Falls back to ~/StreamPanel if APPDATA unset."""
    base = os.environ.get("APPDATA")
    if base:
        root = Path(base)
    else:
        root = Path.home()
    p = root / _APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def default_shortcuts_dir() -> Path:
    """Directory where `.lnk` / `.url` deck files live."""
    p = user_data_dir() / "shortcuts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def resolve_shortcuts_dir(override: Path | str | None) -> Path:
    """Use ``override`` if it is an existing directory; otherwise ``default_shortcuts_dir()``."""
    if override is None:
        return default_shortcuts_dir()
    p = Path(override).expanduser()
    try:
        p = p.resolve()
    except OSError:
        return default_shortcuts_dir()
    if p.is_dir():
        return p
    return default_shortcuts_dir()


def default_db_path() -> Path:
    """SQLite database path."""
    return user_data_dir() / "streampanel.db"
