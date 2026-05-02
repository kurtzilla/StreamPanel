"""Channels viewer stub; primary deck action opens here until the lower pane exists."""

from __future__ import annotations

import customtkinter as ctk

from streampanel.store import DeckItem
from streampanel.window_chrome import COLOR_BG


def open_channels_for_item(parent: ctk.CTk, item: DeckItem) -> None:
    win = ctk.CTkToplevel(parent)
    win.title("Channels")
    win.geometry("420x200")
    win.minsize(360, 160)
    win.transient(parent)
    win.configure(fg_color=COLOR_BG)
    win.attributes("-topmost", True)
    win.after(120, lambda: win.attributes("-topmost", False))

    outer = ctk.CTkFrame(win, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=16, pady=16)
    ctk.CTkLabel(
        outer,
        text="Channels (stub — lower pane later)",
        font=ctk.CTkFont(size=14, weight="bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 8))
    ctk.CTkLabel(
        outer,
        text=item.source_path,
        wraplength=380,
        justify="left",
        anchor="w",
        text_color=("gray75", "gray70"),
    ).pack(fill="both", expand=True, pady=(0, 12))
    ctk.CTkButton(outer, text="Close", command=win.destroy, width=100).pack(anchor="e")
