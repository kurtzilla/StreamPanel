"""Modal editor for a single deck item (label, notes, icon, confirm flag)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from streampanel import store, themes
from streampanel.icon_image import load_ctk_image_for_path
from streampanel.window_chrome import _stub_dialog

_FLAG_CONFIRM = "confirm_launch"
_PREVIEW_PX = 48


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
    win.geometry("480x640")
    win.minsize(420, 560)
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

    ctk.CTkLabel(outer, text="Deck icon (optional)", anchor="w").pack(fill="x", pady=(0, 4))
    icon_row = ctk.CTkFrame(outer, fg_color="transparent")
    icon_row.pack(fill="x", pady=(0, 4))
    icon_row.grid_columnconfigure(0, weight=1)
    icon_entry = ctk.CTkEntry(icon_row, placeholder_text=r".ico, image, or .exe / .dll")
    icon_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    if item.icon_path:
        icon_entry.insert(0, item.icon_path)

    preview_lbl = ctk.CTkLabel(outer, text="No preview", anchor="w")
    preview_lbl.pack(fill="x", pady=(0, 8))

    def refresh_preview(_event: object | None = None) -> None:
        raw = icon_entry.get().strip()
        img = load_ctk_image_for_path(raw, size_px=_PREVIEW_PX) if raw else None
        if img is not None:
            preview_lbl.configure(image=img, text="")
        else:
            preview_lbl.configure(image=None, text="No preview" if not raw else "Could not load preview")
        preview_lbl.image = img  # type: ignore[attr-defined]

    def browse_icon() -> None:
        fp = filedialog.askopenfilename(
            parent=win,
            title="Choose icon file",
            filetypes=(
                ("Icon / image", "*.ico *.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("Programs / libraries", "*.exe *.dll"),
                ("All files", "*.*"),
            ),
        )
        if not fp:
            return
        icon_entry.delete(0, "end")
        icon_entry.insert(0, fp)
        refresh_preview()

    def clear_icon_field() -> None:
        icon_entry.delete(0, "end")
        refresh_preview()

    ctk.CTkButton(icon_row, text="Browse…", width=76, command=browse_icon).grid(
        row=0, column=1, padx=(0, 4), sticky="e"
    )
    ctk.CTkButton(icon_row, text="Clear", width=56, command=clear_icon_field).grid(
        row=0, column=2, sticky="e"
    )

    icon_entry.bind("<KeyRelease>", refresh_preview)
    refresh_preview()

    ctk.CTkLabel(outer, text="Notes", anchor="w").pack(fill="x", pady=(0, 4))
    notes_box = ctk.CTkTextbox(outer, height=100, wrap="word")
    notes_box.pack(fill="both", expand=True, pady=(0, 8))
    if item.notes:
        notes_box.insert("1.0", item.notes)

    flags = store.parse_flags(item)
    confirm_var = ctk.BooleanVar(value=bool(flags.get(_FLAG_CONFIRM)))
    ctk.CTkCheckBox(
        outer,
        text="Confirm before launch",
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

    win.protocol("WM_DELETE_WINDOW", dismiss)
    win.bind("<Escape>", lambda _e: dismiss())

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
            icon_raw = icon_entry.get().strip()
            if icon_raw:
                ip = Path(icon_raw)
                if not ip.is_file():
                    _stub_dialog(win, "Icon file", "Icon path must be an existing file.")
                    return
                resolved = str(ip.resolve())
                ok = store.update_item(
                    c2,
                    item_id,
                    clear_label_override=not bool(label_text),
                    label_override=label_text if label_text else None,
                    clear_notes=not bool(notes_raw),
                    notes=notes_raw if notes_raw else None,
                    icon_path=resolved,
                    flags=merged,
                )
            else:
                ok = store.update_item(
                    c2,
                    item_id,
                    clear_label_override=not bool(label_text),
                    label_override=label_text if label_text else None,
                    clear_notes=not bool(notes_raw),
                    notes=notes_raw if notes_raw else None,
                    clear_icon_path=True,
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

    win.after_idle(lambda: label_entry.focus_set())
