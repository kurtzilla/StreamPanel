"""Open shortcut files with the OS default handler.

Windows uses ``os.startfile`` (same as Explorer for ``.url`` / ``.lnk``).
Other platforms are not supported in v1; call sites should catch
``NotImplementedError`` and show a clear message.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


class ShellOpenError(Exception):
    """Raised when the path is not an openable file or the OS refused the open."""


def open_path(path: str | Path) -> None:
    """Resolve *path*, ensure it is a regular file, then hand it to the OS shell.

    :raises ShellOpenError: if the path is missing or not a file, or ``startfile`` fails.
    :raises NotImplementedError: on non-Windows (no implementation in this version).
    """
    p = Path(path).expanduser()
    try:
        p = p.resolve()
    except OSError as e:
        raise ShellOpenError(f"Could not resolve path: {e}") from e

    if not p.is_file():
        raise ShellOpenError(f"Not a file or missing: {p}")

    if sys.platform != "win32":
        raise NotImplementedError(
            "Opening shortcuts with the default application is only implemented on Windows in this version."
        )

    try:
        os.startfile(str(p), "open")
    except OSError as e:
        raise ShellOpenError(str(e)) from e
