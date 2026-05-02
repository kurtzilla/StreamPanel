"""Minimal CTk shell with deck grid (see deck_grid)."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from streampanel import single_instance, store, themes, win_monitors
from streampanel.add_link_dialog import open_add_link_dialog
from streampanel.panel_dnd import install_panel_drop_handlers
from streampanel.channels_view import open_channels_for_item
from streampanel.deck_grid import DeckGridView, item_matches_search
from streampanel.item_editor import open_item_editor
from streampanel.item_launch import try_launch_deck_item
from streampanel.settings_dialog import open_settings_dialog
from streampanel.panel_layout import (
    cap_shell_width_excess,
    clamp_root_geometry,
    deck_intrinsic_width,
    max_panel_height,
    min_panel_height,
    min_panel_width,
)
from streampanel.shortcuts_folder import (
    PortableDataDirError,
    resolve_shortcuts_dir,
    user_data_dir,
)
from streampanel.win_overlay import apply_tool_window_overlay, set_tool_window_excluded
from streampanel.window_chrome import (
    _stub_dialog,
    apply_borderless_chrome,
    refresh_chrome_theme,
)

_FILTER_ENTRY_WIDTH_BASE = 200


def _apply_ui_scale(scale: float) -> None:
    s = store.clamp_ui_scale(float(scale))
    ctk.set_widget_scaling(s)
    ctk.set_window_scaling(s)


def _count_hidden(all_items: list[store.DeckItem], settings: store.AppSettings) -> int:
    if settings.deck_show_hidden_items:
        return 0
    return sum(1 for it in all_items if store.item_hidden_from_deck(it))


def _footer_status_line(n_db: int, n_hidden: int, sync: store.SyncResult) -> str:
    """One-line summary for the footer under the deck (no folder path)."""
    parts = [
        f"{n_db} in DB",
        f"sync +{len(sync.added_paths)}/−{len(sync.removed_ids)}",
    ]
    if n_hidden > 0:
        parts.append(f"{n_hidden} hidden")
    return " · ".join(parts)


def run() -> None:
    try:
        data_root = user_data_dir()
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

    single_instance.acquire_or_exit(data_dir=data_root)

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
    footer_line = _footer_status_line(
        len(all_items),
        _count_hidden(all_items, app_settings),
        sync,
    )

    shell_state: dict[str, bool] = {"top": shell.always_on_top}
    deck_cell_px_ref: list[int] = [app_settings.deck_cell_px]
    min_h = min_panel_height(len(visible), grid_cols_ref[0], deck_cell_px_ref[0])
    max_h0 = max_panel_height(len(visible), grid_cols_ref[0], deck_cell_px_ref[0])
    min_w0 = min_panel_width(len(visible), grid_cols_ref[0], deck_cell_px_ref[0])
    mons0 = win_monitors.list_work_monitors(None)
    _ml, _mt, mr, _mb = win_monitors.virtual_desktop_span(mons0)
    virtual_span_w = max(1, mr - _ml)

    intrinsic_w0 = deck_intrinsic_width(grid_cols_ref[0], deck_cell_px_ref[0])

    if (
        shell.w is not None
        and shell.h is not None
        and shell.x is not None
        and shell.y is not None
    ):
        w_use = cap_shell_width_excess(
            win_monitors.sanitize_restored_shell_width(
                shell.w, virtual_span_w, min_w0
            ),
            min_w0,
            intrinsic_w0,
        )
        h_use = max(min_h, min(shell.h, max_h0))
        mon = win_monitors.monitor_for_panel_center(
            shell.x, shell.y, w_use, h_use, mons0
        )
        if app_settings.window_startup_placement == store.WINDOW_STARTUP_LAST_POSITION:
            x_in, y_in = shell.x, shell.y
        else:
            x_in = win_monitors.top_center_x(mon, w_use)
            y_in = mon.top
        x0, y0, w1, h1 = clamp_root_geometry(
            x_in,
            y_in,
            w_use,
            h_use,
            vroot_x=mon.left,
            vroot_y=mon.top,
            vroot_w=mon.width,
            vroot_h=mon.height,
            max_w=mon.width,
            min_w=min_w0,
            min_h=min_h,
            max_h=min(max_h0, mon.height),
        )
        root.geometry(f"{w1}x{h1}+{x0}+{y0}")
    else:
        m0 = win_monitors.primary_or_first(mons0)
        x0 = m0.left + max(0, (m0.width - min_w0) // 2)
        y0 = m0.top
        h0 = max(min_h, 220)
        h0 = min(h0, max_h0, m0.height)
        root.geometry(f"{min_w0}x{h0}+{x0}+{y0}")

    root.minsize(min_w0, min_h)

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
        root.update_idletasks()
        min_h2 = min_panel_height(n_ref[0], grid_cols_ref[0], deck_cell_px_ref[0])
        max_h2 = max_panel_height(n_ref[0], grid_cols_ref[0], deck_cell_px_ref[0])
        mons = win_monitors.list_work_monitors(root)
        x, y = root.winfo_x(), root.winfo_y()
        w, h = root.winfo_width(), root.winfo_height()
        min_w2 = min_panel_width(n_ref[0], grid_cols_ref[0], deck_cell_px_ref[0])
        intrinsic_deck = deck_intrinsic_width(grid_cols_ref[0], deck_cell_px_ref[0])
        try:
            not_mapped = int(root.winfo_viewable()) == 0
        except Exception:
            not_mapped = False
        if not_mapped or w < max(40, min_w2 // 2) or h < max(40, min_h2 // 2):
            m0 = win_monitors.primary_or_first(mons)
            root.minsize(min_w2, min_h2)
            root.maxsize(m0.width, min(max_h2, m0.height))
            return
        w_before_cap = w
        w = cap_shell_width_excess(w, min_w2, intrinsic_deck)
        mon = win_monitors.monitor_for_panel_center(x, y, w, h, mons)
        max_h_cap = min(max_h2, mon.height)
        if w != w_before_cap and y == mon.top:
            x = win_monitors.top_center_x(mon, w)
        x, y, w, h = clamp_root_geometry(
            x,
            y,
            w,
            h,
            vroot_x=mon.left,
            vroot_y=mon.top,
            vroot_w=mon.width,
            vroot_h=mon.height,
            max_w=mon.width,
            min_w=min_w2,
            min_h=min_h2,
            max_h=max_h_cap,
        )
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.maxsize(mon.width, max_h_cap)
        root.minsize(min_w2, min_h2)
        if len(mons) > 1:
            try:
                idx = next(
                    i
                    for i, t in enumerate(mons)
                    if (t.left, t.top, t.right, t.bottom)
                    == (mon.left, mon.top, mon.right, mon.bottom)
                )
            except StopIteration:
                idx = 0
            raw = getattr(root, "_streampanel_chrome", None)
            if isinstance(raw, dict):
                mbs = raw.get("monitor_buttons")
                if mbs:
                    pal = themes.current_palette()
                    for i, b in enumerate(mbs):
                        if i == idx:
                            b.configure(fg_color=pal.strip_button_hover)
                        else:
                            b.configure(fg_color="transparent")
        persist_now()

    footer_status_holder: list[ctk.CTkLabel | None] = [None]
    filter_title_holder: list[ctk.CTkLabel | None] = [None]
    search_entry_holder: list[ctk.CTkEntry | None] = [None]

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
        lbl = footer_status_holder[0]
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
            text=_footer_status_line(
                len(all_items),
                _count_hidden(all_items, st),
                sy,
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
        deck_cell_px_ref[0] = settings.deck_cell_px
        dg = deck_grid_holder[0]
        if dg is not None:
            dg.set_cols(settings.grid_cols)
            dg.set_cell_px(settings.deck_cell_px)
        reload_deck()
        root.update_idletasks()
        fs = footer_status_holder[0]
        if fs is not None:
            fs.configure(text_color=themes.current_palette().drag_hint_text)
        se = search_entry_holder[0]
        if se is not None:
            se.configure(
                width=int(
                    _FILTER_ENTRY_WIDTH_BASE * store.clamp_ui_scale(settings.ui_scale)
                )
            )
        ft = filter_title_holder[0]
        if ft is not None:
            ft.configure(text_color=themes.current_palette().drag_hint_text)

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

    def _top_rail_snap(px: int, x: int, y: int, w: int, h: int) -> tuple[int, int]:
        return win_monitors.snap_top_rail(
            x,
            y,
            w,
            h,
            win_monitors.list_work_monitors(root),
            pointer_x=px,
        )

    def _on_monitor_menu(choice: str) -> None:
        def _apply_monitor_move() -> None:
            mons = win_monitors.list_work_monitors(root)
            idx = win_monitors.parse_display_choice(str(choice), len(mons))
            if idx is None:
                return
            m = mons[idx]
            root.update_idletasks()
            w, h = root.winfo_width(), root.winfo_height()
            min_w2 = min_panel_width(n_ref[0], grid_cols_ref[0], deck_cell_px_ref[0])
            min_h2 = min_panel_height(n_ref[0], grid_cols_ref[0], deck_cell_px_ref[0])
            max_h2 = max_panel_height(n_ref[0], grid_cols_ref[0], deck_cell_px_ref[0])
            try:
                not_mapped = int(root.winfo_viewable()) == 0
            except Exception:
                not_mapped = False
            if not_mapped or w < max(40, min_w2 // 2) or h < max(40, min_h2 // 2):
                w, h = min_w2, min_h2
            w = max(min_w2, min(w, m.width))
            h = min(max(min_h2, h), max_h2, m.height)
            x = win_monitors.top_center_x(m, w)
            y = m.top
            root.geometry(f"{w}x{h}+{x}+{y}")
            flush_layout_and_persist()

        root.after(0, _apply_monitor_move)

    mon_labels = [f"Display {i + 1}" for i in range(len(mons0))]

    body = apply_borderless_chrome(
        root,
        always_on_top=shell_state["top"],
        on_pin_toggled=on_pin_toggled,
        on_settings=on_settings,
        on_close=on_close,
        top_rail_snap=_top_rail_snap,
        monitor_values=mon_labels if len(mons0) > 1 else None,
        on_monitor_selected=_on_monitor_menu if len(mons0) > 1 else None,
    )

    inner = ctk.CTkFrame(body, fg_color="transparent")
    inner.pack(expand=True, fill="both", padx=20, pady=16)
    inner.grid_columnconfigure(0, weight=1)
    inner.grid_columnconfigure(1, weight=0)
    inner.grid_columnconfigure(2, weight=1)
    inner.grid_rowconfigure(0, weight=1)

    deck_center_slot = ctk.CTkFrame(inner, fg_color="transparent")
    deck_center_slot.grid(row=0, column=1, sticky="n")

    deck_grid_holder[0] = DeckGridView(
        deck_center_slot,
        cols=grid_cols_ref[0],
        cell_px=deck_cell_px_ref[0],
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
    deck_grid_holder[0].widget.pack(anchor="n", pady=(0, 6))

    footer = ctk.CTkFrame(inner, fg_color="transparent")
    footer.grid(row=1, column=0, columnspan=3, sticky="ew")
    footer.grid_columnconfigure(0, weight=0)
    footer.grid_columnconfigure(1, weight=1)

    _fpal = themes.current_palette()
    filter_fr = ctk.CTkFrame(footer, fg_color="transparent")
    filter_fr.grid(row=0, column=0, sticky="w")
    filter_title = ctk.CTkLabel(
        filter_fr,
        text="Filter",
        font=ctk.CTkFont(size=12),
        text_color=_fpal.drag_hint_text,
        anchor="e",
    )
    filter_title.pack(side="left", padx=(0, 6))
    filter_title_holder[0] = filter_title
    search_entry = ctk.CTkEntry(
        filter_fr,
        placeholder_text="Label or path…",
        width=int(
            _FILTER_ENTRY_WIDTH_BASE * store.clamp_ui_scale(app_settings.ui_scale)
        ),
        height=28,
        font=ctk.CTkFont(size=12),
    )
    search_entry.pack(side="left")
    search_entry_holder[0] = search_entry

    status_footer = ctk.CTkLabel(
        footer,
        text=footer_line,
        font=ctk.CTkFont(size=12),
        text_color=_fpal.drag_hint_text,
        anchor="e",
        justify="right",
    )
    status_footer.grid(row=0, column=1, sticky="ew", padx=(10, 0))
    footer_status_holder[0] = status_footer

    def on_search_change(_event: object | None = None) -> None:
        search_ref[0] = search_entry.get()
        apply_deck_filter()

    search_entry.bind("<KeyRelease>", on_search_change)

    def on_configure(event: object) -> None:
        ev = event  # type: ignore[assignment]
        if ev.widget is not root:
            return
        schedule_persist()

    root.bind("<Configure>", on_configure)

    def _root_focus_in(_event: object | None = None) -> None:
        # Modal CTkToplevels use a different toplevel; while they have focus the main
        # window may not show a taskbar button (acceptable until we track transients).
        set_tool_window_excluded(root, False)

    def _root_focus_out(_event: object | None = None) -> None:
        def maybe_exclude() -> None:
            try:
                w = root.focus_get()
            except Exception:
                w = None
            if w is None:
                set_tool_window_excluded(root, True)
                return
            try:
                if w.winfo_toplevel() is root:
                    return
            except Exception:
                pass
            set_tool_window_excluded(root, True)

        root.after_idle(maybe_exclude)

    root.bind("<FocusIn>", _root_focus_in)
    root.bind("<FocusOut>", _root_focus_out)

    root.after_idle(lambda: root.after(0, flush_layout_and_persist))
    def _post_map_shell() -> None:
        single_instance.register_main_window_hwnd(root, data_root)
        apply_tool_window_overlay(root)

    root.after(100, _post_map_shell)

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
