"""Minimal CTk shell with deck grid (see deck_grid)."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from streampanel import store, themes
from streampanel.add_link_dialog import open_add_link_dialog
from streampanel.panel_dnd import install_panel_drop_handlers
from streampanel.channels_view import open_channels_for_item
from streampanel.deck_grid import DeckGridView, item_matches_search
from streampanel.item_editor import open_item_editor
from streampanel.item_launch import try_launch_deck_item
from streampanel.settings_dialog import open_settings_dialog
from streampanel.panel_layout import (
    MIN_PANEL_WIDTH,
    clamp_root_geometry,
    max_panel_height,
    min_panel_height,
)
from streampanel.shortcuts_folder import (
    PortableDataDirError,
    resolve_shortcuts_dir,
    user_data_dir,
)
from streampanel.win_overlay import apply_tool_window_overlay
from streampanel.window_chrome import (
    _stub_dialog,
    apply_borderless_chrome,
    refresh_chrome_theme,
)

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
    try:
        user_data_dir()
    except PortableDataDirError as e:
        d = store.default_app_settings()
        ctk.set_appearance_mode(d.appearance_mode)
        _apply_ui_scale(d.ui_scale)
        err_root = ctk.CTk()
        err_root.title("StreamPanel")
        themes.apply_theme(d.ui_theme, d.appearance_mode)
        _stub_dialog(err_root, "StreamPanel data folder", str(e))
        err_root.destroy()
        return

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
    themes.apply_theme(app_settings.ui_theme, app_settings.appearance_mode)

    shortcuts_ref: list[Path] = [shortcuts]
    grid_cols_ref: list[int] = [app_settings.grid_cols]
    app_settings_ref: list[store.AppSettings] = [app_settings]

    items_ref: list[list[store.DeckItem]] = [visible]
    search_ref: list[str] = [""]
    n_ref = [0]
    subtitle = _sync_subtitle(
        len(all_items),
        _count_hidden(all_items, app_settings),
        sync,
        shortcuts,
    )

    shell_state: dict[str, bool] = {"top": shell.always_on_top}
    min_h = min_panel_height(len(visible), grid_cols_ref[0])

    if (
        shell.w is not None
        and shell.h is not None
        and shell.x is not None
        and shell.y is not None
    ):
        root.geometry(f"{shell.w}x{shell.h}+{shell.x}+{shell.y}")
    else:
        root.geometry("600x220")

    root.minsize(MIN_PANEL_WIDTH, min_h)

    debounce_id: list[int | None] = [None]

    def screen_number_int() -> int:
        # Tcl 9 / some Windows Tk builds omit winfo screennumber; Python 3.13 may lack the wrapper.
        wsn = getattr(root, "winfo_screennumber", None)
        if callable(wsn):
            sn = wsn()
            if isinstance(sn, int):
                return sn
            try:
                return int(sn)
            except (TypeError, ValueError):
                pass
        name = root.winfo_screen()
        if isinstance(name, str) and "." in name:
            try:
                return int(name.rsplit(".", 1)[-1])
            except ValueError:
                pass
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

    def on_deck_double_click(it: store.DeckItem) -> None:
        try_launch_deck_item(root, it)

    def apply_deck_filter() -> None:
        """Rebuild grid from ``items_ref`` and ``search_ref``; updates ``n_ref`` for layout."""
        dg = deck_grid_holder[0]
        if dg is None:
            return
        st = app_settings_ref[0]
        q = search_ref[0]
        shown = [it for it in items_ref[0] if item_matches_search(it, q)]
        n_ref[0] = len(shown)
        delay = (
            350 if st.deck_primary_action == store.DECK_PRIMARY_CHANNELS else 0
        )
        double_cb = (
            on_deck_double_click
            if st.deck_primary_action == store.DECK_PRIMARY_CHANNELS
            else None
        )
        dg.set_primary_interaction(
            primary_click_delay_ms=delay,
            on_item_double_click=double_cb,
        )
        dg.set_reorder_handler(on_deck_reorder if not q.strip() else None)
        dg.rebuild(shown)
        flush_layout_and_persist()

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
        finally:
            c.close()
        lbl.configure(
            text=_sync_subtitle(
                len(all_items),
                _count_hidden(all_items, st),
                sy,
                shortcuts_ref[0],
            )
        )
        apply_deck_filter()

    def after_new_link_saved(path: Path, deck_icon: str | None) -> None:
        if not deck_icon:
            return
        c = store.connect()
        try:
            iid = store.get_item_id_for_source_path(c, path)
            if iid is not None:
                store.update_item(c, iid, icon_path=deck_icon)
        finally:
            c.close()
        reload_deck()

    def on_add_link() -> None:
        open_add_link_dialog(
            root,
            shortcuts_dir=shortcuts_ref[0],
            on_created=reload_deck,
            after_save=after_new_link_saved,
        )

    def on_applied(settings: store.AppSettings) -> None:
        app_settings_ref[0] = settings
        shortcuts_ref[0] = resolve_shortcuts_dir(settings.shortcuts_dir)
        ctk.set_appearance_mode(settings.appearance_mode)
        _apply_ui_scale(settings.ui_scale)
        themes.apply_theme(settings.ui_theme, settings.appearance_mode)
        refresh_chrome_theme(root)
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
        st = app_settings_ref[0]
        if st.deck_primary_action == store.DECK_PRIMARY_LAUNCH:
            try_launch_deck_item(root, it)
            return
        open_channels_for_item(root, it)
        c = store.connect()
        try:
            store.record_item_open(c, item_id=it.id, source_path=it.source_path)
        finally:
            c.close()

    def on_item_edit(it: store.DeckItem) -> None:
        open_item_editor(root, it.id, on_saved=reload_deck)

    def on_deck_reorder(from_idx: int, to_idx: int) -> None:
        if search_ref[0].strip():
            return
        vis = list(items_ref[0])
        ids = [it.id for it in vis]
        moved = ids.pop(from_idx)
        ids.insert(to_idx, moved)
        c = store.connect()
        try:
            full = [it.id for it in store.list_items(c)]
            vis_set = frozenset(ids)
            merged = store.merge_full_order_after_visible_reorder(
                full, ids, visible_id_set=vis_set
            )
            store.reorder_items(c, merged)
        finally:
            c.close()
        reload_deck()

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

    search_row = ctk.CTkFrame(inner, fg_color="transparent")
    search_row.pack(fill="x", pady=(0, 8))
    search_row.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(search_row, text="Filter deck", anchor="w").grid(
        row=0, column=0, padx=(0, 8), sticky="w"
    )
    search_entry = ctk.CTkEntry(
        search_row,
        placeholder_text="Substring matches label or path…",
    )
    search_entry.grid(row=0, column=1, sticky="ew")

    def on_search_change(_event: object | None = None) -> None:
        search_ref[0] = search_entry.get()
        apply_deck_filter()

    search_entry.bind("<KeyRelease>", on_search_change)

    deck_grid_holder[0] = DeckGridView(
        inner,
        cols=grid_cols_ref[0],
        on_item_primary=on_item_primary,
        on_item_edit=on_item_edit,
        on_add=on_add_link,
        on_reorder=on_deck_reorder,
        primary_click_delay_ms=(
            350
            if app_settings.deck_primary_action == store.DECK_PRIMARY_CHANNELS
            else 0
        ),
        on_item_double_click=(
            on_deck_double_click
            if app_settings.deck_primary_action == store.DECK_PRIMARY_CHANNELS
            else None
        ),
    )
    apply_deck_filter()
    deck_grid_holder[0].widget.pack(fill="both", expand=True)

    def on_configure(event: object) -> None:
        ev = event  # type: ignore[assignment]
        if ev.widget is not root:
            return
        schedule_persist()

    root.bind("<Configure>", on_configure)

    root.after_idle(lambda: root.after(0, flush_layout_and_persist))
    root.after(100, lambda: apply_tool_window_overlay(root))

    install_panel_drop_handlers(
        root,
        get_shortcuts_dir=lambda: shortcuts_ref[0],
        on_reload_deck=reload_deck,
        after_new_link=after_new_link_saved,
    )

    def _accel_grab_clear() -> bool:
        try:
            return root.grab_current() is None
        except Exception:
            return True

    def _accel_settings(_event: object | None = None) -> str | None:
        if not _accel_grab_clear():
            return None
        on_settings()
        return "break"

    def _accel_add_link(_event: object | None = None) -> str | None:
        if not _accel_grab_clear():
            return None
        on_add_link()
        return "break"

    root.bind("<Control-comma>", _accel_settings)
    root.bind("<Control-n>", _accel_add_link)

    root.mainloop()
