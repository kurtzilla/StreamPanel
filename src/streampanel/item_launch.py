"""Open a deck shortcut with the OS handler; confirm flag, errors, and launch telemetry."""

from __future__ import annotations

import customtkinter as ctk

from streampanel import store
from streampanel.runtime_shell import ShellOpenError, open_path
from streampanel.store import DeckItem
from streampanel.window_chrome import _stub_dialog, confirm_dialog

_FLAG_CONFIRM = "confirm_launch"


def try_launch_deck_item(parent: ctk.CTk, item: DeckItem) -> bool:
    """Open *item* with the default application and record a ``launch`` event.

    Honors ``confirm_launch`` in item flags. Shows ``_stub_dialog`` on failure.
    Returns True if the file was opened and the event was recorded.
    """
    flags = store.parse_flags(item)
    if flags.get(_FLAG_CONFIRM):
        if not confirm_dialog(
            parent,
            "Confirm launch",
            "Open this shortcut with the default application?",
        ):
            return False
    try:
        open_path(item.source_path)
    except NotImplementedError as e:
        _stub_dialog(parent, "Not supported", str(e))
        return False
    except ShellOpenError as e:
        _stub_dialog(parent, "Could not open", str(e))
        return False
    c = store.connect()
    try:
        store.record_item_open(
            c,
            item_id=item.id,
            source_path=item.source_path,
            kind="launch",
        )
    finally:
        c.close()
    return True
