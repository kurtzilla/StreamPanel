"""Modal to add an internet shortcut (.url) into the shortcuts folder."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import customtkinter as ctk

from streampanel.window_chrome import COLOR_BG, _stub_dialog

_MAX_STEM_LEN = 120
_INVALID_WIN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def normalize_url(raw: str) -> str:
    s = raw.strip()
    if not s:
        raise ValueError("URL is empty.")
    parsed = urlparse(s)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://.")
    netloc = parsed.netloc
    if not netloc:
        raise ValueError("URL must include a host (e.g. https://example.com).")
    netloc = netloc.lower()
    return urlunparse(
        (parsed.scheme.lower(), netloc, parsed.path or "", "", parsed.query, parsed.fragment)
    )


def internet_shortcut_body(url: str) -> str:
    return f"[InternetShortcut]\nURL={url}\n"


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
    on_created: Callable[[], None] | None = None,
) -> None:
    shortcuts_dir = shortcuts_dir.resolve()
    shortcuts_dir.mkdir(parents=True, exist_ok=True)

    win = ctk.CTkToplevel(parent)
    win.title("Add link")
    win.geometry("440x280")
    win.minsize(380, 260)
    win.transient(parent)
    win.configure(fg_color=COLOR_BG)
    win.attributes("-topmost", True)
    win.after(120, lambda: win.attributes("-topmost", False))
    win.grab_set()

    outer = ctk.CTkFrame(win, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=16, pady=16)

    ctk.CTkLabel(outer, text="URL (https://…)", anchor="w").pack(fill="x", pady=(0, 4))
    url_entry = ctk.CTkEntry(outer, placeholder_text="https://example.com/page")
    url_entry.pack(fill="x", pady=(0, 10))

    ctk.CTkLabel(
        outer,
        text="Filename (optional, without .url)",
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    stem_entry = ctk.CTkEntry(outer, placeholder_text="Leave empty to use host from URL")
    stem_entry.pack(fill="x", pady=(0, 16))

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
        body = internet_shortcut_body(url)
        try:
            path.write_text(body, encoding="utf-8", newline="\n")
        except OSError as e:
            _stub_dialog(win, "Could not save", str(e))
            return
        dismiss()
        if on_created is not None:
            on_created()

    ctk.CTkButton(btn_row, text="Cancel", command=dismiss, width=100).pack(
        side="right", padx=(8, 0)
    )
    ctk.CTkButton(btn_row, text="Add", command=add, width=100).pack(side="right")
