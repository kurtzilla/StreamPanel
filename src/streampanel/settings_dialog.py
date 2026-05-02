"""Modal settings editor: appearance, shortcuts folder, grid columns."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from streampanel import store
from streampanel.window_chrome import COLOR_BG, _stub_dialog


def open_settings_dialog(
    parent: ctk.CTk,
    *,
    on_saved: Callable[[store.AppSettings], None] | None = None,
) -> None:
    conn = store.connect()
    try:
        current = store.load_app_settings(conn)
    finally:
        conn.close()

    win = ctk.CTkToplevel(parent)
    win.title("Settings")
    win.geometry("480x400")
    win.minsize(420, 360)
    win.transient(parent)
    win.configure(fg_color=COLOR_BG)
    win.attributes("-topmost", True)
    win.after(120, lambda: win.attributes("-topmost", False))
    win.grab_set()

    outer = ctk.CTkFrame(win, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=16, pady=16)

    ctk.CTkLabel(outer, text="Appearance", anchor="w").pack(fill="x", pady=(0, 4))
    appearance_menu = ctk.CTkOptionMenu(outer, values=list(store.APPEARANCE_MODES))
    appearance_menu.pack(fill="x", pady=(0, 12))
    appearance_menu.set(current.appearance_mode)

    ctk.CTkLabel(outer, text="Shortcuts folder (empty = default)", anchor="w").pack(
        fill="x", pady=(0, 4)
    )
    path_row = ctk.CTkFrame(outer, fg_color="transparent")
    path_row.pack(fill="x", pady=(0, 12))
    path_row.grid_columnconfigure(0, weight=1)
    path_entry = ctk.CTkEntry(path_row, placeholder_text="Default app folder")
    path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    if current.shortcuts_dir is not None:
        path_entry.insert(0, str(current.shortcuts_dir))

    def browse() -> None:
        initial = path_entry.get().strip()
        if initial:
            ip = Path(initial).expanduser()
            try:
                ip = ip.resolve()
            except OSError:
                ip = None
            initial_dir = str(ip) if ip is not None and ip.is_dir() else None
        else:
            initial_dir = None
        picked = filedialog.askdirectory(
            parent=win,
            title="Shortcuts folder",
            initialdir=initial_dir or str(Path.home()),
        )
        if picked:
            path_entry.delete(0, "end")
            path_entry.insert(0, picked)

    ctk.CTkButton(path_row, text="Browse…", width=88, command=browse).grid(row=0, column=1)

    col_labels = [str(n) for n in range(store.GRID_COLS_MIN, store.GRID_COLS_MAX + 1)]
    ctk.CTkLabel(outer, text="Deck columns", anchor="w").pack(fill="x", pady=(0, 4))
    grid_menu = ctk.CTkOptionMenu(outer, values=col_labels)
    grid_menu.pack(fill="x", pady=(0, 16))
    grid_menu.set(str(store.clamp_grid_cols(current.grid_cols)))

    show_hidden_var = ctk.BooleanVar(value=current.deck_show_hidden_items)
    ctk.CTkCheckBox(
        outer,
        text="Show items hidden from deck on the grid",
        variable=show_hidden_var,
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
        appearance_mode = appearance_menu.get()
        if appearance_mode not in store.APPEARANCE_MODES:
            appearance_mode = store.default_app_settings().appearance_mode

        raw_path = path_entry.get().strip()
        shortcuts_dir: Path | None = None
        if raw_path:
            p = Path(raw_path).expanduser()
            try:
                p = p.resolve()
            except OSError:
                _stub_dialog(win, "Invalid path", "Could not resolve that folder path.")
                return
            if not p.is_dir():
                _stub_dialog(
                    win,
                    "Not a folder",
                    "Choose an existing directory, or clear the field for the default folder.",
                )
                return
            shortcuts_dir = p

        try:
            grid_cols = int(grid_menu.get())
        except ValueError:
            grid_cols = store.default_app_settings().grid_cols
        grid_cols = store.clamp_grid_cols(grid_cols)

        settings = store.AppSettings(
            appearance_mode=appearance_mode,
            shortcuts_dir=shortcuts_dir,
            grid_cols=grid_cols,
            deck_show_hidden_items=bool(show_hidden_var.get()),
        )
        c2 = store.connect()
        try:
            store.save_app_settings(c2, settings)
        finally:
            c2.close()
        dismiss()
        if on_saved is not None:
            on_saved(settings)

    ctk.CTkButton(btn_row, text="Cancel", command=dismiss, width=100).pack(
        side="right", padx=(8, 0)
    )
    ctk.CTkButton(btn_row, text="Save", command=save, width=100).pack(side="right")
