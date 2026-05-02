"""Modal to add an internet shortcut (.url) into the shortcuts folder."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import customtkinter as ctk

from streampanel import themes
from streampanel.url_shortcut import (
    ParsedInternetShortcut,
    internet_shortcut_body,
    normalize_url,
)
from streampanel.window_chrome import _stub_dialog

_MAX_STEM_LEN = 120
_INVALID_WIN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename_stem(stem: str) -> str:
    s = _INVALID_WIN_CHARS.sub("-", stem.strip())
    s = re.sub(r"-{2,}", "-", s).strip(" .-")
    if len(s) > _MAX_STEM_LEN:
        s = s[:_MAX_STEM_LEN].rstrip(" .-")
    return s


def default_stem_from_url(url: str) -> str:
    p = urlparse(url)
    host = p.netloc.split("@")[-1]
    if ":" in host and not host.startswith("["):
        host = host.rsplit(":", 1)[0]
    path = p.path.strip("/").replace("/", "-")
    path = _INVALID_WIN_CHARS.sub("-", path)
    path = re.sub(r"-{2,}", "-", path).strip(" .-")[:40]
    if path:
        return f"{host}-{path}" if host else path or "link"
    return host or "link"


def pick_unique_url_filename(shortcuts_dir: Path, stem: str) -> Path:
    safe = sanitize_filename_stem(stem)
    if not safe:
        safe = "link"
    n = 1
    while n < 10_000:
        name = f"{safe}.url" if n == 1 else f"{safe}-{n}.url"
        path = shortcuts_dir / name
        if not path.exists():
            return path
        n += 1
    raise RuntimeError("Could not pick a unique .url filename.")


def open_add_link_dialog(
    parent: ctk.CTk,
    *,
    shortcuts_dir: Path,
    preset: ParsedInternetShortcut | None = None,
    suggested_filename_stem: str | None = None,
    on_created: Callable[[], None] | None = None,
    after_save: Callable[[Path, str | None], None] | None = None,
) -> None:
    shortcuts_dir = shortcuts_dir.resolve()
    shortcuts_dir.mkdir(parents=True, exist_ok=True)

    win = ctk.CTkToplevel(parent)
    win.title("Add link")
    win.geometry("480x420")
    win.minsize(420, 380)
    win.transient(parent)
    win.configure(fg_color=themes.dialog_background())
    win.attributes("-topmost", True)
    win.after(120, lambda: win.attributes("-topmost", False))
    win.grab_set()

    outer = ctk.CTkFrame(win, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=16, pady=16)

    ctk.CTkLabel(outer, text="URL (https://…)", anchor="w").pack(fill="x", pady=(0, 4))
    url_entry = ctk.CTkEntry(outer, placeholder_text="https://example.com/page")
    url_entry.pack(fill="x", pady=(0, 8))
    if preset is not None:
        url_entry.insert(0, preset.url)

    ctk.CTkLabel(
        outer,
        text="Filename (optional, without .url)",
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    stem_entry = ctk.CTkEntry(outer, placeholder_text="Leave empty to use host from URL")
    stem_entry.pack(fill="x", pady=(0, 8))
    if suggested_filename_stem:
        stem_entry.insert(0, sanitize_filename_stem(suggested_filename_stem))
    elif preset is not None and not stem_entry.get().strip():
        stem_entry.insert(0, default_stem_from_url(preset.url))

    ctk.CTkLabel(
        outer,
        text="Icon file (optional, .ico / image / .exe)",
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    icon_entry = ctk.CTkEntry(outer, placeholder_text=r"C:\path\to\icon.ico")
    icon_entry.pack(fill="x", pady=(0, 4))
    if preset is not None and preset.icon_file:
        icon_entry.insert(0, preset.icon_file)

    ctk.CTkLabel(outer, text="Icon index", anchor="w").pack(fill="x", pady=(0, 4))
    icon_index_entry = ctk.CTkEntry(outer, placeholder_text="0")
    icon_index_entry.pack(fill="x", pady=(0, 12))
    if preset is not None:
        icon_index_entry.insert(0, str(preset.icon_index))

    btn_row = ctk.CTkFrame(outer, fg_color="transparent")
    btn_row.pack(fill="x")

    def dismiss() -> None:
        try:
            win.grab_release()
        except Exception:
            pass
        win.destroy()

    def add() -> None:
        raw_url = url_entry.get()
        try:
            url = normalize_url(raw_url)
        except ValueError as e:
            _stub_dialog(win, "Invalid URL", str(e))
            return
        stem_raw = stem_entry.get().strip()
        stem = stem_raw if stem_raw else default_stem_from_url(url)
        path = pick_unique_url_filename(shortcuts_dir, stem)

        icon_raw = icon_entry.get().strip()
        try:
            icon_idx = int(icon_index_entry.get().strip() or "0")
        except ValueError:
            _stub_dialog(win, "Invalid icon index", "Icon index must be an integer.")
            return

        icon_for_ini: str | None = None
        deck_icon: str | None = None
        if icon_raw:
            ip = Path(icon_raw)
            if not ip.is_file():
                _stub_dialog(win, "Icon file", "Icon file path must be an existing file.")
                return
            icon_for_ini = str(ip)
            deck_icon = str(ip.resolve())

        body = internet_shortcut_body(url, icon_file=icon_for_ini, icon_index=icon_idx)
        try:
            path.write_text(body, encoding="utf-8", newline="\n")
        except OSError as e:
            _stub_dialog(win, "Could not save", str(e))
            return
        dismiss()
        if on_created is not None:
            on_created()
        if after_save is not None:
            after_save(path, deck_icon)

    ctk.CTkButton(btn_row, text="Cancel", command=dismiss, width=100).pack(
        side="right", padx=(8, 0)
    )
    ctk.CTkButton(btn_row, text="Add", command=add, width=100).pack(side="right")
