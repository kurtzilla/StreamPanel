"""Minimal CTk shell; window chrome and deck UI come in later slices."""

from __future__ import annotations

import customtkinter as ctk

from streampanel import store
from streampanel.shortcuts_folder import default_shortcuts_dir


def run() -> None:
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.title("StreamPanel")
    root.geometry("460x200")
    root.minsize(320, 140)

    conn = store.connect()
    try:
        shortcuts = default_shortcuts_dir()
        sync = store.sync_from_folder(conn, shortcuts)
        n = len(store.list_items(conn))
        subtitle = (
            f"{n} shortcut(s) in DB — sync +{len(sync.added_paths)} / −{len(sync.removed_ids)}. "
            f"Folder:\n{shortcuts}"
        )
    finally:
        conn.close()

    frame = ctk.CTkFrame(root, fg_color="transparent")
    frame.pack(expand=True, fill="both", padx=24, pady=24)

    ctk.CTkLabel(
        frame,
        text="StreamPanel",
        font=ctk.CTkFont(size=20, weight="bold"),
    ).pack(pady=(0, 8))
    ctk.CTkLabel(
        frame,
        text=subtitle,
        wraplength=420,
        justify="left",
    ).pack()

    root.mainloop()
