"""Channels window: shortcut path, Launch, notes, and recent view/launch history."""

from __future__ import annotations

from datetime import datetime, timezone

import customtkinter as ctk

from streampanel import store, themes
from streampanel.item_launch import try_launch_deck_item
from streampanel.store import DeckItem


def _format_activity_line(ev: store.LaunchEventRow) -> str:
    try:
        iso = ev.opened_at.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone()
        ts = local.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        ts = ev.opened_at
    if ev.kind == "launch":
        label = "Launched"
    elif ev.kind == "view":
        label = "Viewed"
    else:
        label = ev.kind
    return f"{ts} — {label}"


def open_channels_for_item(parent: ctk.CTk, item: DeckItem) -> None:
    win = ctk.CTkToplevel(parent)
    win.title("Channels")
    win.geometry("500x560")
    win.minsize(420, 440)
    win.transient(parent)
    win.configure(fg_color=themes.dialog_background())
    win.attributes("-topmost", True)
    win.after(120, lambda: win.attributes("-topmost", False))

    outer = ctk.CTkFrame(win, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=16, pady=16)

    upper = ctk.CTkFrame(outer, fg_color="transparent")
    upper.pack(fill="x", pady=(0, 8))
    ctk.CTkLabel(
        upper,
        text="Channels",
        font=ctk.CTkFont(size=14, weight="bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    ctk.CTkLabel(
        upper,
        text="Use Launch to open this shortcut in your default app (browser for .url, target for .lnk).",
        wraplength=440,
        justify="left",
        anchor="w",
        text_color=("gray75", "gray70"),
    ).pack(fill="x", pady=(0, 8))
    ctk.CTkLabel(
        upper,
        text=item.source_path,
        wraplength=440,
        justify="left",
        anchor="w",
        text_color=("gray75", "gray70"),
    ).pack(fill="x", pady=(0, 12))

    btn_row = ctk.CTkFrame(upper, fg_color="transparent")
    btn_row.pack(fill="x")

    lower = ctk.CTkFrame(outer, fg_color="transparent")
    lower.pack(fill="both", expand=True)

    ctk.CTkLabel(
        lower,
        text="Notes",
        font=ctk.CTkFont(size=12, weight="bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    notes_body = (item.notes or "").strip() or "No notes for this shortcut."
    notes_box = ctk.CTkTextbox(lower, height=100, wrap="word", font=ctk.CTkFont(size=12))
    notes_box.pack(fill="x", pady=(0, 12))
    notes_box.insert("1.0", notes_body)
    notes_box.configure(state="disabled")

    ctk.CTkLabel(
        lower,
        text="Recent activity",
        font=ctk.CTkFont(size=12, weight="bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 4))

    activity_host = ctk.CTkScrollableFrame(lower, fg_color="transparent")
    activity_host.pack(fill="both", expand=True)

    def refresh_activity() -> None:
        for w in activity_host.winfo_children():
            w.destroy()
        c = store.connect()
        try:
            events = store.list_launch_events_for_item(c, item.id, limit=25)
        finally:
            c.close()
        if not events:
            ctk.CTkLabel(
                activity_host,
                text="No views or launches recorded yet.",
                anchor="w",
                justify="left",
                text_color=("gray75", "gray70"),
            ).pack(anchor="w")
        else:
            for ev in events:
                ctk.CTkLabel(
                    activity_host,
                    text=_format_activity_line(ev),
                    anchor="w",
                    justify="left",
                ).pack(fill="x", pady=(0, 2))

    refresh_activity()

    def on_launch() -> None:
        if try_launch_deck_item(win, item):
            refresh_activity()

    ctk.CTkButton(btn_row, text="Close", command=win.destroy, width=100).pack(side="right")
    ctk.CTkButton(btn_row, text="Launch", command=on_launch, width=100).pack(
        side="right", padx=(0, 8)
    )
