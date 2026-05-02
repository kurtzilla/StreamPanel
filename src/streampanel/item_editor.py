"""Modal editor for a single deck item (label, notes, confirm flag)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from streampanel import store, themes
from streampanel.window_chrome import _stub_dialog

_FLAG_CONFIRM = "confirm_launch"


def open_item_editor(
    parent: ctk.CTk,
    item_id: int,
    *,
    on_saved: Callable[[], None] | None = None,
) -> None:
    conn = store.connect()
    try:
        item = store.get_item(conn, item_id)
    finally:
        conn.close()
    if item is None:
        _stub_dialog(parent, "Shortcut missing", "That shortcut is no longer in the database.")
        return

    win = ctk.CTkToplevel(parent)
    win.title("Edit shortcut")
    win.geometry("440x520")
    win.minsize(380, 460)
    win.transient(parent)
    win.configure(fg_color=themes.dialog_background())
    win.attributes("-topmost", True)
    win.after(120, lambda: win.attributes("-topmost", False))
    win.grab_set()

    outer = ctk.CTkFrame(win, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=16, pady=16)

    ctk.CTkLabel(
        outer,
        text="Source (read-only)",
        font=ctk.CTkFont(size=12, weight="bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    path_text = item.source_path
    ctk.CTkLabel(
        outer,
        text=path_text,
        wraplength=400,
        justify="left",
        anchor="w",
        text_color=("gray75", "gray70"),
    ).pack(fill="x", pady=(0, 12))

    ctk.CTkLabel(outer, text="Display label (empty = use filename)", anchor="w").pack(
        fill="x", pady=(0, 4)
    )
    label_entry = ctk.CTkEntry(outer, placeholder_text=Path(item.source_path).stem)
    label_entry.pack(fill="x", pady=(0, 8))
    if item.label_override:
        label_entry.insert(0, item.label_override)

    ctk.CTkLabel(outer, text="Notes", anchor="w").pack(fill="x", pady=(0, 4))
    notes_box = ctk.CTkTextbox(outer, height=100, wrap="word")
    notes_box.pack(fill="both", expand=True, pady=(0, 8))
    if item.notes:
        notes_box.insert("1.0", item.notes)

    flags = store.parse_flags(item)
    confirm_var = ctk.BooleanVar(value=bool(flags.get(_FLAG_CONFIRM)))
    ctk.CTkCheckBox(
        outer,
        text="Confirm before launch (Channels)",
        variable=confirm_var,
    ).pack(anchor="w", pady=(0, 6))
    hide_var = ctk.BooleanVar(value=bool(flags.get(store.FLAG_HIDE_FROM_DECK)))
    ctk.CTkCheckBox(
        outer,
        text="Hide from deck (keep in library)",
        variable=hide_var,
    ).pack(anchor="w", pady=(0, 16))

    btn_row = ctk.CTkFrame(outer, fg_color="transparent")
    btn_row.pack(fill="x")

    def dismiss() -> None:
        try:
            win.grab_release()
        except Exception:
            pass
        win.destroy()

    def save() -> None:
        c2 = store.connect()
        try:
            cur = store.get_item(c2, item_id)
            if cur is None:
                _stub_dialog(win, "Shortcut missing", "It was removed while you were editing.")
                dismiss()
                return
            label_text = label_entry.get().strip()
            notes_raw = notes_box.get("1.0", "end-1c").strip()
            merged = store.parse_flags(cur).copy()
            merged[_FLAG_CONFIRM] = bool(confirm_var.get())
            merged[store.FLAG_HIDE_FROM_DECK] = bool(hide_var.get())
            ok = store.update_item(
                c2,
                item_id,
                clear_label_override=not bool(label_text),
                label_override=label_text if label_text else None,
                clear_notes=not bool(notes_raw),
                notes=notes_raw if notes_raw else None,
                flags=merged,
            )
        finally:
            c2.close()
        if not ok:
            _stub_dialog(win, "Save failed", "Could not update this shortcut.")
            return
        dismiss()
        if on_saved is not None:
            on_saved()

    ctk.CTkButton(btn_row, text="Cancel", command=dismiss, width=100).pack(
        side="right", padx=(8, 0)
    )
    ctk.CTkButton(btn_row, text="Save", command=save, width=100).pack(side="right")
