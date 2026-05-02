"""Channels viewer: staging area until the lower pane exists; system launch here."""

from __future__ import annotations

import customtkinter as ctk

from streampanel import store
from streampanel.runtime_shell import ShellOpenError, open_path
from streampanel.store import DeckItem
from streampanel.window_chrome import COLOR_BG, _stub_dialog, confirm_dialog

_FLAG_CONFIRM = "confirm_launch"


def open_channels_for_item(parent: ctk.CTk, item: DeckItem) -> None:
    win = ctk.CTkToplevel(parent)
    win.title("Channels")
    win.geometry("440x260")
    win.minsize(400, 220)
    win.transient(parent)
    win.configure(fg_color=COLOR_BG)
    win.attributes("-topmost", True)
    win.after(120, lambda: win.attributes("-topmost", False))

    outer = ctk.CTkFrame(win, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=16, pady=16)
    ctk.CTkLabel(
        outer,
        text="Channels",
        font=ctk.CTkFont(size=14, weight="bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    ctk.CTkLabel(
        outer,
        text="Use Launch to open this shortcut in your default app (browser for .url, target for .lnk).",
        wraplength=400,
        justify="left",
        anchor="w",
        text_color=("gray75", "gray70"),
    ).pack(fill="x", pady=(0, 8))
    ctk.CTkLabel(
        outer,
        text=item.source_path,
        wraplength=400,
        justify="left",
        anchor="w",
        text_color=("gray75", "gray70"),
    ).pack(fill="both", expand=True, pady=(0, 12))

    btn_row = ctk.CTkFrame(outer, fg_color="transparent")
    btn_row.pack(fill="x")

    def try_launch() -> None:
        flags = store.parse_flags(item)
        if flags.get(_FLAG_CONFIRM):
            if not confirm_dialog(
                win,
                "Confirm launch",
                "Open this shortcut with the default application?",
            ):
                return
        try:
            open_path(item.source_path)
        except NotImplementedError as e:
            _stub_dialog(win, "Not supported", str(e))
            return
        except ShellOpenError as e:
            _stub_dialog(win, "Could not open", str(e))
            return
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

    ctk.CTkButton(btn_row, text="Close", command=win.destroy, width=100).pack(side="right")
    ctk.CTkButton(btn_row, text="Launch", command=try_launch, width=100).pack(
        side="right", padx=(0, 8)
    )
