"""Optional drag-and-drop onto the panel (``tkinterdnd2``)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from streampanel import store
from streampanel.add_link_dialog import open_add_link_dialog
from streampanel.url_shortcut import (
    ParsedInternetShortcut,
    looks_like_single_http_url,
    normalize_url,
    parse_internet_shortcut,
)
from streampanel.window_chrome import _stub_dialog

# tkinterdnd2 patches BaseWidget; Python 3.13's Tk subclasses Misc only (BaseWidget subclasses Misc),
# so CTk/tk.Tk never see drop_target_register unless we mirror the hooks onto Misc.
_DND_MISC_ATTRS = (
    "_subst_format_dnd",
    "_subst_format_str_dnd",
    "_substitute_dnd",
    "_dnd_bind",
    "dnd_bind",
    "drag_source_register",
    "drag_source_unregister",
    "drop_target_register",
    "drop_target_unregister",
    "platform_independent_types",
    "platform_specific_types",
    "get_dropfile_tempdir",
    "set_dropfile_tempdir",
)


def _ensure_tkdnd_on_misc() -> None:
    import tkinter as tk

    if hasattr(tk.Misc, "drop_target_register"):
        return
    bw = tk.BaseWidget
    for name in _DND_MISC_ATTRS:
        if hasattr(bw, name):
            setattr(tk.Misc, name, getattr(bw, name))


def paths_from_dnd_files(data: str) -> list[Path]:
    s = data.strip()
    if not s:
        return []
    if "{" in s:
        paths: list[Path] = []
        rest = s
        while "{" in rest:
            a = rest.find("{")
            b = rest.find("}", a)
            if b == -1:
                break
            paths.append(Path(rest[a + 1 : b]))
            rest = rest[b + 1 :].lstrip()
        return paths
    return [Path(x) for x in s.split() if x]


def _drag_drop_url_already_listed(root: ctk.CTk, normalized_url: str) -> bool:
    """If the URL is already used by a ``.url`` in the library, show a dialog and return True."""
    c = store.connect()
    try:
        exists = store.deck_has_normalized_url(c, normalized_url)
    finally:
        c.close()
    if not exists:
        return False
    _stub_dialog(
        root,
        "URL already in shortcuts",
        "That address is already used by a link in your shortcuts folder. "
        "Drag-and-drop only adds links whose URL is not already in the list.\n\n"
        "You can still add another tile with the same URL using **Add link** on the toolbar "
        "(for example after copying an existing shortcut).",
    )
    return True


def install_panel_drop_handlers(
    root: ctk.CTk,
    *,
    get_shortcuts_dir: Callable[[], Path],
    on_reload_deck: Callable[[], None],
    after_new_link: Callable[[Path, str | None], None],
    ensure_expanded: Callable[[], None] | None = None,
) -> bool:
    """Register ``<<Drop>>`` on *root* if tkinterdnd2 is available. Returns True if installed."""
    try:
        from tkinterdnd2 import DND_FILES, DND_TEXT, TkinterDnD
    except ImportError:
        return False

    _ensure_tkdnd_on_misc()
    TkinterDnD._require(root)

    def on_drop(event: object) -> None:
        data = getattr(event, "data", None)
        if not isinstance(data, str):
            return
        if ensure_expanded is not None:
            ensure_expanded()
        shortcuts_dir = get_shortcuts_dir()

        for p in paths_from_dnd_files(data):
            if p.suffix.lower() != ".url":
                continue
            try:
                preset = parse_internet_shortcut(p)
            except ValueError:
                continue
            if _drag_drop_url_already_listed(root, preset.url):
                return
            open_add_link_dialog(
                root,
                shortcuts_dir=shortcuts_dir,
                preset=preset,
                suggested_filename_stem=p.stem,
                on_created=on_reload_deck,
                after_save=after_new_link,
            )
            return

        if looks_like_single_http_url(data.strip()):
            try:
                url = normalize_url(data.strip())
            except ValueError:
                return
            preset = ParsedInternetShortcut(
                url=url,
                icon_file=None,
                icon_index=0,
                working_directory=None,
            )
            if _drag_drop_url_already_listed(root, url):
                return
            open_add_link_dialog(
                root,
                shortcuts_dir=shortcuts_dir,
                preset=preset,
                on_created=on_reload_deck,
                after_save=after_new_link,
            )

    root.drop_target_register(DND_FILES, DND_TEXT)
    root.dnd_bind("<<Drop>>", on_drop)
    return True
