"""Minimal CTk shell with deck grid (see deck_grid)."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from streampanel import store
from streampanel.add_link_dialog import open_add_link_dialog
from streampanel.channels_view import open_channels_for_item
from streampanel.deck_grid import DeckGridView
from streampanel.item_editor import open_item_editor
from streampanel.settings_dialog import open_settings_dialog
from streampanel.panel_layout import (
    MIN_PANEL_WIDTH,
    clamp_root_geometry,
    max_panel_height,
    min_panel_height,
)
from streampanel.shortcuts_folder import resolve_shortcuts_dir
from streampanel.win_overlay import apply_tool_window_overlay
from streampanel.window_chrome import apply_borderless_chrome

_SUBTITLE_WRAP_BASE = 430


def _apply_ui_scale(scale: float) -> None:
    s = store.clamp_ui_scale(float(scale))
    ctk.set_widget_scaling(s)
    ctk.set_window_scaling(s)


def _count_hidden(all_items: list[store.DeckItem], settings: store.AppSettings) -> int:
    if settings.deck_show_hidden_items:
        return 0
    return sum(1 for it in all_items if store.item_hidden_from_deck(it))


def _sync_subtitle(n_db: int, n_hidden: int, sync: store.SyncResult, shortcuts: object) -> str:
    lines = [
        f"{n_db} shortcut(s) in DB — sync +{len(sync.added_paths)} / −{len(sync.removed_ids)}.",
        f"Shortcuts folder:\n{shortcuts}",
    ]
    if n_hidden > 0:
        lines.append(
            f'{n_hidden} hidden from deck (enable "Show items hidden from deck on the grid" in Settings).'
        )
    return "\n".join(lines)


def run() -> None:
    conn = store.connect()
    try:
        app_settings = store.load_app_settings(conn)
        shortcuts = resolve_shortcuts_dir(app_settings.shortcuts_dir)
        sync = store.sync_from_folder(conn, shortcuts)
        all_items = store.list_items(conn)
        visible = store.list_deck_items(conn, app_settings)
        shell = store.load_panel_shell_state(conn)
    finally:
        conn.close()

    ctk.set_appearance_mode(app_settings.appearance_mode)
    _apply_ui_scale(app_settings.ui_scale)
    root = ctk.CTk()
    root.title("StreamPanel")

    shortcuts_ref: list[Path] = [shortcuts]
    grid_cols_ref: list[int] = [app_settings.grid_cols]
    app_settings_ref: list[store.AppSettings] = [app_settings]

    items_ref: list[list[store.DeckItem]] = [visible]
    n_ref = [len(items_ref[0])]
    subtitle = _sync_subtitle(
        len(all_items),
        _count_hidden(all_items, app_settings),
        sync,
        shortcuts,
    )

    shell_state: dict[str, bool] = {"top": shell.always_on_top}
    min_h = min_panel_height(n_ref[0], grid_cols_ref[0])

    if (
        shell.w is not None
        and shell.h is not None
        and shell.x is not None
        and shell.y is not None
    ):
        root.geometry(f"{shell.w}x{shell.h}+{shell.x}+{shell.y}")
    else:
        root.geometry("480x220")

    root.minsize(MIN_PANEL_WIDTH, min_h)

    debounce_id: list[int | None] = [None]

    def screen_number_int() -> int:
        sn = root.winfo_screennumber()
        if isinstance(sn, int):
            return sn
        try:
            return int(sn)
        except (TypeError, ValueError):
            return 0

    def persist_now() -> None:
        c2 = store.connect()
        try:
            store.save_panel_shell_state(
                c2,
                always_on_top=shell_state["top"],
                x=root.winfo_x(),
                y=root.winfo_y(),
                w=root.winfo_width(),
                h=root.winfo_height(),
                screen_number=screen_number_int(),
            )
        finally:
            c2.close()

    def schedule_persist(_event: object | None = None) -> None:
        if debounce_id[0] is not None:
            root.after_cancel(debounce_id[0])
        debounce_id[0] = root.after(250, flush_layout_and_persist)

    def on_pin_toggled(v: bool) -> None:
        shell_state["top"] = v
        persist_now()

    def on_close() -> None:
        persist_now()
        root.destroy()

    deck_grid_holder: list[DeckGridView | None] = [None]

    def flush_layout_and_persist() -> None:
        debounce_id[0] = None
        min_h2 = min_panel_height(n_ref[0], grid_cols_ref[0])
        max_h2 = max_panel_height(n_ref[0], grid_cols_ref[0])
        sw = root.winfo_screenwidth()
        vx, vy = root.winfo_vrootx(), root.winfo_vrooty()
        vw, vh = root.winfo_vrootwidth(), root.winfo_vrootheight()
        x, y = root.winfo_x(), root.winfo_y()
        w, h = root.winfo_width(), root.winfo_height()
        x, y, w, h = clamp_root_geometry(
            x,
            y,
            w,
            h,
            vroot_x=vx,
            vroot_y=vy,
            vroot_w=vw,
            vroot_h=vh,
            max_w=sw,
            min_w=MIN_PANEL_WIDTH,
            min_h=min_h2,
            max_h=max_h2,
        )
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.maxsize(sw, max_h2)
        root.minsize(MIN_PANEL_WIDTH, min_h2)
        dg = deck_grid_holder[0]
        if dg is not None:
            dg.sync_extra_row(root.winfo_height(), n_ref[0])
        persist_now()

    subtitle_lbl_holder: list[ctk.CTkLabel | None] = [None]

    def reload_deck() -> None:
        dg = deck_grid_holder[0]
        lbl = subtitle_lbl_holder[0]
        if dg is None or lbl is None:
            return
        st = app_settings_ref[0]
        c = store.connect()
        try:
            sy = store.sync_from_folder(c, shortcuts_ref[0])
            all_items = store.list_items(c)
            items_ref[0] = store.list_deck_items(c, st)
            n_ref[0] = len(items_ref[0])
        finally:
            c.close()
        dg.rebuild(items_ref[0])
        lbl.configure(
            text=_sync_subtitle(
                len(all_items),
                _count_hidden(all_items, st),
                sy,
                shortcuts_ref[0],
            )
        )
        flush_layout_and_persist()

    def on_add_link() -> None:
        open_add_link_dialog(root, shortcuts_dir=shortcuts_ref[0], on_created=reload_deck)

    def on_applied(settings: store.AppSettings) -> None:
        app_settings_ref[0] = settings
        shortcuts_ref[0] = resolve_shortcuts_dir(settings.shortcuts_dir)
        ctk.set_appearance_mode(settings.appearance_mode)
        _apply_ui_scale(settings.ui_scale)
        grid_cols_ref[0] = settings.grid_cols
        dg = deck_grid_holder[0]
        if dg is not None:
            dg.set_cols(settings.grid_cols)
        reload_deck()
        lbl = subtitle_lbl_holder[0]
        if lbl is not None:
            lbl.configure(
                wraplength=int(_SUBTITLE_WRAP_BASE * store.clamp_ui_scale(settings.ui_scale))
            )

    def on_settings() -> None:
        open_settings_dialog(root, on_saved=on_applied)

    def on_item_primary(it: store.DeckItem) -> None:
        open_channels_for_item(root, it)
        c = store.connect()
        try:
            store.record_item_open(c, item_id=it.id, source_path=it.source_path)
        finally:
            c.close()

    def on_item_edit(it: store.DeckItem) -> None:
        open_item_editor(root, it.id, on_saved=reload_deck)

    body = apply_borderless_chrome(
        root,
        always_on_top=shell_state["top"],
        on_pin_toggled=on_pin_toggled,
        on_settings=on_settings,
        on_add_link=on_add_link,
        on_close=on_close,
    )

    inner = ctk.CTkFrame(body, fg_color="transparent")
    inner.pack(expand=True, fill="both", padx=20, pady=16)

    ctk.CTkLabel(
        inner,
        text="Status",
        font=ctk.CTkFont(size=16, weight="bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 6))
    subtitle_lbl = ctk.CTkLabel(
        inner,
        text=subtitle,
        wraplength=int(_SUBTITLE_WRAP_BASE * store.clamp_ui_scale(app_settings.ui_scale)),
        justify="left",
        anchor="w",
    )
    subtitle_lbl.pack(fill="x", pady=(0, 8))
    subtitle_lbl_holder[0] = subtitle_lbl

    deck_grid_holder[0] = DeckGridView(
        inner,
        cols=grid_cols_ref[0],
        on_item_primary=on_item_primary,
        on_item_edit=on_item_edit,
        on_add=on_add_link,
    )
    deck_grid_holder[0].rebuild(items_ref[0])
    deck_grid_holder[0].widget.pack(fill="both", expand=True)

    def on_configure(event: object) -> None:
        ev = event  # type: ignore[assignment]
        if ev.widget is not root:
            return
        schedule_persist()

    root.bind("<Configure>", on_configure)

    root.after_idle(lambda: root.after(0, flush_layout_and_persist))
    root.after(100, lambda: apply_tool_window_overlay(root))

    root.mainloop()
