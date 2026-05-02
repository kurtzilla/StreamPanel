"""Resolve StreamPanel user data and shortcuts directory paths (Windows-first)."""

from __future__ import annotations

import os
from pathlib import Path

_APP_NAME = "StreamPanel"

# When set to a non-empty value, all app data (DB, default shortcuts) lives under this directory.
DATA_DIR_ENV = "STREAMPANEL_DATA_DIR"


class PortableDataDirError(Exception):
    """``STREAMPANEL_DATA_DIR`` is set but cannot be used as the user data directory."""


def user_data_dir() -> Path:
    """
    Per-user data root (created on demand).

    If ``STREAMPANEL_DATA_DIR`` is set to a non-empty string, that path is expanded,
    resolved, and created; the database and default shortcuts folder use it.

    Otherwise: ``%APPDATA%/StreamPanel`` (created), or ``~/StreamPanel`` if ``APPDATA`` is unset.
    """
    raw = os.environ.get(DATA_DIR_ENV, "").strip()
    if raw:
        p = Path(raw).expanduser()
        try:
            p = p.resolve()
        except OSError as e:
            raise PortableDataDirError(
                f"{DATA_DIR_ENV} is not a valid path ({raw!r}): {e}"
            ) from e
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise PortableDataDirError(
                f"Cannot create or open {DATA_DIR_ENV} directory {p}: {e}"
            ) from e
        if not p.is_dir():
            raise PortableDataDirError(
                f"{DATA_DIR_ENV} must be a directory, not a file: {p}"
            )
        return p

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
