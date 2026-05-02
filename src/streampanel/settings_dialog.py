"""Modal settings editor: theme, UI scale, shortcuts folder, data backup."""

from __future__ import annotations

import importlib.metadata
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import tkinter
from tkinter import filedialog

import customtkinter as ctk

from streampanel import store, themes
from streampanel.shortcuts_folder import (
    default_db_path,
    resolve_shortcuts_dir,
    user_data_dir,
)
from streampanel.window_chrome import _stub_dialog, confirm_dialog


def _app_version() -> str:
    try:
        return importlib.metadata.version("streampanel")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0"


def _diagnostics_block(settings: store.AppSettings) -> str:
    c = store.connect()
    try:
        all_items = store.list_items(c)
        deck = store.list_deck_items(c, settings)
    finally:
        c.close()
    n_total = len(all_items)
    n_deck = len(deck)
    n_hidden = sum(1 for it in all_items if store.item_hidden_from_deck(it))
    db_path = default_db_path()
    sc_dir = resolve_shortcuts_dir(settings.shortcuts_dir)
    py_line = sys.version.replace("\n", " ")
    lines = [
        f"StreamPanel version: {_app_version()}",
        f"Python: {py_line}",
        f"Platform: {sys.platform}",
        f"Database: {db_path}",
        f"Shortcuts folder (resolved): {sc_dir}",
        f"Items — total: {n_total}, on deck: {n_deck}, hidden-from-deck: {n_hidden}",
    ]
    return "\n".join(lines)


def _open_user_data_dir() -> None:
    p = user_data_dir()
    if sys.platform == "win32":
        os.startfile(str(p))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(p)], check=False)
    else:
        subprocess.Popen(["xdg-open", str(p)], check=False)


class _Tooltip:
    def __init__(self, parent: ctk.CTkToplevel) -> None:
        self._parent = parent
        self._win: tkinter.Toplevel | None = None

    def show(self, text: str, x: int, y: int) -> None:
        self.hide()
        w = tkinter.Toplevel(self._parent)
        w.wm_overrideredirect(True)
        w.attributes("-topmost", True)
        tkinter.Label(
            w,
            text=text,
            justify="left",
            wraplength=400,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("", 10),
        ).pack(ipadx=6, ipady=4)
        w.geometry(f"+{x + 14}+{y + 14}")
        self._win = w

    def hide(self) -> None:
        if self._win is not None:
            try:
                self._win.destroy()
            except tkinter.TclError:
                pass
            self._win = None


def _bind_menu_hover_tooltips(
    option_menu: ctk.CTkOptionMenu,
    *,
    parent: ctk.CTkToplevel,
    tips: dict[str, str],
) -> None:
    menu = getattr(option_menu, "_dropdown_menu", None)
    if menu is None:
        return
    tip = _Tooltip(parent)

    def on_motion(e: tkinter.Event) -> None:
        try:
            idx = menu.index(f"@{e.x},{e.y}")
        except tkinter.TclError:
            tip.hide()
            return
        if idx < 0:
            tip.hide()
            return
        try:
            lab = str(menu.entrycget(idx, "label"))
        except tkinter.TclError:
            tip.hide()
            return
        t = tips.get(lab, "")
        if t:
            tip.show(t, int(e.x_root), int(e.y_root))
        else:
            tip.hide()

    def on_leave(_e: object | None = None) -> None:
        tip.hide()

    menu.bind("<Motion>", on_motion, add="+")
    menu.bind("<Leave>", on_leave, add="+")
    menu.bind("<Unmap>", on_leave, add="+")


def open_settings_dialog(
    parent: ctk.CTk,
    *,
    on_saved: Callable[[store.AppSettings], None] | None = None,
    on_always_on_top_changed: Callable[[bool], None] | None = None,
) -> None:
    conn = store.connect()
    try:
        current = store.load_app_settings(conn)
        shell = store.load_panel_shell_state(conn)
    finally:
        conn.close()

    win = ctk.CTkToplevel(parent)
    win.title("Settings")
    win.geometry("520x720")
    win.minsize(440, 520)
    win.transient(parent)
    win.configure(fg_color=themes.dialog_background())
    win.attributes("-topmost", True)
    win.after(120, lambda: win.attributes("-topmost", False))
    win.grab_set()

    outer = ctk.CTkFrame(win, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=16, pady=16)

    theme_labels = [themes.THEME_LABELS[tid] for tid in themes.THEME_IDS]
    label_to_theme = {themes.THEME_LABELS[tid]: tid for tid in themes.THEME_IDS}

    ctk.CTkLabel(outer, text="Theme", anchor="w").pack(fill="x", pady=(0, 4))
    theme_menu = ctk.CTkOptionMenu(outer, values=theme_labels)
    theme_menu.pack(fill="x", pady=(0, 12))
    theme_menu.set(themes.THEME_LABELS[themes.clamp_theme_id(current.ui_theme)])

    preset_labels = [lbl for lbl, _ in store.UI_SCALE_PRESETS]
    preset_by_label = {lbl: v for lbl, v in store.UI_SCALE_PRESETS}
    nearest = store.nearest_ui_scale_preset_value(current.ui_scale)
    initial_scale_label = next(
        lbl for lbl, v in store.UI_SCALE_PRESETS if v == nearest
    )

    ctk.CTkLabel(outer, text="Interface scale", anchor="w").pack(fill="x", pady=(0, 4))
    scale_menu = ctk.CTkOptionMenu(outer, values=preset_labels)
    scale_menu.pack(fill="x", pady=(0, 12))
    scale_menu.set(initial_scale_label)

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
            _mark_dirty()

    ctk.CTkButton(path_row, text="Browse…", width=88, command=browse).grid(row=0, column=1)

    ctk.CTkLabel(outer, text="Deck tile size (pixels)", anchor="w").pack(
        fill="x", pady=(0, 4)
    )
    ctk.CTkLabel(
        outer,
        text=f"Presets or custom ({store.DECK_CELL_PX_MIN}–{store.DECK_CELL_PX_MAX} px).",
        anchor="w",
        justify="left",
        wraplength=440,
        text_color=("gray75", "gray70"),
    ).pack(fill="x", pady=(0, 6))

    tile_row = ctk.CTkFrame(outer, fg_color="transparent")
    tile_row.pack(fill="x", pady=(0, 4))
    cell_custom_entry = ctk.CTkEntry(tile_row, width=72, placeholder_text="px")
    tile_buttons: dict[int, ctk.CTkButton] = {}
    tile_mode: list[str] = ["50"]  # "25" | "50" | "75" | "custom"

    def _sync_tile_buttons() -> None:
        m = tile_mode[0]
        pal = themes.current_palette()
        for step, btn in tile_buttons.items():
            sel = m == str(step)
            btn.configure(
                fg_color=pal.strip_button_hover if sel else "transparent",
                border_width=1,
            )

    def _set_tile_step(step: int) -> None:
        tile_mode[0] = str(step)
        cell_custom_entry.delete(0, "end")
        cell_custom_entry.configure(state="disabled")
        _sync_tile_buttons()
        _mark_dirty()

    def _set_tile_custom() -> None:
        tile_mode[0] = "custom"
        cell_custom_entry.configure(state="normal")
        _sync_tile_buttons()
        _mark_dirty()

    for step in (25, 50, 75):
        b = ctk.CTkButton(
            tile_row,
            text=str(step),
            width=52,
            command=lambda s=step: _set_tile_step(s),
        )
        b.pack(side="left", padx=(0, 6))
        tile_buttons[step] = b
    ctk.CTkButton(tile_row, text="Custom", width=72, command=_set_tile_custom).pack(
        side="left", padx=(0, 8)
    )
    cell_custom_entry.pack(side="left")

    init_px = store.clamp_deck_cell_px(current.deck_cell_px)
    if init_px in (25, 50, 75):
        tile_mode[0] = str(init_px)
        cell_custom_entry.configure(state="disabled")
    else:
        tile_mode[0] = "custom"
        cell_custom_entry.insert(0, str(init_px))
        cell_custom_entry.configure(state="normal")
    _sync_tile_buttons()

    def _deck_cell_px_from_ui() -> int:
        if tile_mode[0] in ("25", "50", "75"):
            return int(tile_mode[0])
        try:
            return int(cell_custom_entry.get().strip())
        except ValueError:
            return store.default_app_settings().deck_cell_px

    _placement_labels = (
        "Top center on last display",
        "Remember last size and position",
    )
    _placement_label_for: dict[str, str] = {
        store.WINDOW_STARTUP_CENTER: _placement_labels[0],
        store.WINDOW_STARTUP_LAST_POSITION: _placement_labels[1],
    }
    _placement_value_for = {
        _placement_labels[0]: store.WINDOW_STARTUP_CENTER,
        _placement_labels[1]: store.WINDOW_STARTUP_LAST_POSITION,
    }
    _placement_tips = {
        _placement_labels[0]: (
            "Align the panel to the top center of the display that held the window "
            "last session."
        ),
        _placement_labels[1]: (
            "Reopen where you left it (still clamped to the work area)."
        ),
    }

    ctk.CTkLabel(outer, text="When the app starts", anchor="w").pack(
        fill="x", pady=(0, 4)
    )
    placement_menu = ctk.CTkOptionMenu(outer, values=list(_placement_labels))
    placement_menu.pack(fill="x", pady=(0, 12))
    placement_menu.set(
        _placement_label_for.get(
            current.window_startup_placement,
            _placement_labels[0],
        )
    )
    win.after(80, lambda: _bind_menu_hover_tooltips(
        placement_menu, parent=win, tips=_placement_tips
    ))

    show_hidden_var = ctk.BooleanVar(value=current.deck_show_hidden_items)
    ctk.CTkCheckBox(
        outer,
        text="Show items hidden from deck on the grid",
        variable=show_hidden_var,
    ).pack(anchor="w", pady=(0, 8))

    _primary_labels = ("Open Channels", "Launch immediately")
    _primary_label_for: dict[str, str] = {
        store.DECK_PRIMARY_CHANNELS: _primary_labels[0],
        store.DECK_PRIMARY_LAUNCH: _primary_labels[1],
    }
    _primary_action_for = {
        _primary_labels[0]: store.DECK_PRIMARY_CHANNELS,
        _primary_labels[1]: store.DECK_PRIMARY_LAUNCH,
    }

    ctk.CTkLabel(outer, text="Primary deck click", anchor="w").pack(fill="x", pady=(0, 4))
    ctk.CTkLabel(
        outer,
        text="Open Channels: single click opens this window (double-click launches). "
        "Launch immediately: single click runs the shortcut without opening Channels.",
        anchor="w",
        justify="left",
        wraplength=440,
        text_color=("gray75", "gray70"),
    ).pack(fill="x", pady=(0, 6))
    primary_menu = ctk.CTkOptionMenu(outer, values=list(_primary_labels))
    primary_menu.pack(fill="x", pady=(0, 12))
    primary_menu.set(_primary_label_for.get(current.deck_primary_action, _primary_labels[0]))

    always_on_top_var = ctk.BooleanVar(value=shell.always_on_top)
    ctk.CTkCheckBox(
        outer,
        text="Always on top (keep the panel above other windows)",
        variable=always_on_top_var,
    ).pack(anchor="w", pady=(0, 10))

    _drag_anim_displays = ("None", "Fade in", "Slide in")
    _drag_anim_display_for: dict[str, str] = {
        store.PANEL_DRAG_ANIM_NONE: "None",
        store.PANEL_DRAG_ANIM_FADE: "Fade in",
        store.PANEL_DRAG_ANIM_SLIDE: "Slide in",
    }
    _drag_anim_from_display = {v: k for k, v in _drag_anim_display_for.items()}

    ctk.CTkLabel(outer, text="Panel drag animation", anchor="w").pack(
        fill="x", pady=(0, 4)
    )
    ctk.CTkLabel(
        outer,
        text="After you release a strip drag: snap instantly, fade the window in at the new spot, or slide it there.",
        anchor="w",
        justify="left",
        wraplength=440,
        text_color=("gray75", "gray70"),
    ).pack(fill="x", pady=(0, 6))
    drag_anim_menu = ctk.CTkOptionMenu(outer, values=list(_drag_anim_displays))
    drag_anim_menu.pack(fill="x", pady=(0, 12))
    drag_anim_menu.set(
        _drag_anim_display_for.get(
            current.panel_drag_animation,
            "None",
        )
    )

    ctk.CTkLabel(outer, text="Data", anchor="w").pack(fill="x", pady=(0, 4))
    ctk.CTkLabel(
        outer,
        text="Export copies the SQLite database only (deck layout, settings, history). "
        "Shortcut files in your folder are not included.",
        anchor="w",
        justify="left",
        wraplength=440,
    ).pack(fill="x", pady=(0, 8))

    data_row = ctk.CTkFrame(outer, fg_color="transparent")
    data_row.pack(fill="x", pady=(0, 12))

    def export_backup() -> None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        initial = f"streampanel-backup-{stamp}.db"
        path = filedialog.asksaveasfilename(
            parent=win,
            title="Export database backup",
            defaultextension=".db",
            filetypes=[("SQLite database", "*.db"), ("All files", "*.*")],
            initialfile=initial,
        )
        if not path:
            return
        dest = Path(path)
        try:
            store.export_db_to_file(dest)
        except FileNotFoundError:
            _stub_dialog(
                win,
                "Backup failed",
                "The database file was not found. Try restarting the app after a first sync.",
            )
        except OSError as e:
            _stub_dialog(win, "Backup failed", str(e))
        except ValueError as e:
            _stub_dialog(win, "Backup failed", str(e))
        else:
            _stub_dialog(
                win,
                "Backup saved",
                f"Database copy created:\n{dest}",
            )

    def open_data_folder() -> None:
        try:
            _open_user_data_dir()
        except OSError as e:
            _stub_dialog(win, "Could not open folder", str(e))

    ctk.CTkButton(
        data_row,
        text="Export database backup…",
        command=export_backup,
    ).pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        data_row,
        text="Open user data folder",
        width=160,
        command=open_data_folder,
    ).pack(side="left")

    ctk.CTkLabel(outer, text="About / Diagnostics", anchor="w").pack(
        fill="x", pady=(8, 4)
    )
    diag_body = _diagnostics_block(current)
    diag_box = ctk.CTkTextbox(outer, height=110, wrap="word", font=ctk.CTkFont(size=11))
    diag_box.pack(fill="x", pady=(0, 8))
    diag_box.insert("1.0", diag_body)
    diag_box.configure(state="disabled")

    def copy_diagnostics() -> None:
        cx = store.connect()
        try:
            s = store.load_app_settings(cx)
        finally:
            cx.close()
        text = _diagnostics_block(s)
        try:
            win.clipboard_clear()
            win.clipboard_append(text)
            win.update()
        except tkinter.TclError as e:
            _stub_dialog(win, "Copy failed", str(e))
            return
        _stub_dialog(win, "Copied", "Diagnostics copied to the clipboard.")

    ctk.CTkButton(outer, text="Copy diagnostics to clipboard", command=copy_diagnostics).pack(
        fill="x", pady=(0, 4)
    )

    def _path_str_norm() -> str:
        return path_entry.get().strip()

    def _shortcuts_dir_from_path() -> Path | None:
        raw_path = _path_str_norm()
        if not raw_path:
            return None
        p = Path(raw_path).expanduser()
        try:
            p = p.resolve()
        except OSError:
            return None
        if not p.is_dir():
            return None
        return p

    def _snapshot_from_widgets() -> dict[str, object]:
        theme_label = theme_menu.get()
        ui_theme = label_to_theme.get(theme_label, themes.default_theme_id())
        scale_label = scale_menu.get()
        ui_scale = store.clamp_ui_scale(
            preset_by_label.get(scale_label, store.UI_SCALE_DEFAULT)
        )
        sd = _shortcuts_dir_from_path()
        if _path_str_norm() and sd is None:
            sd = "__invalid__"
        plab = primary_menu.get()
        deck_primary_action = _primary_action_for.get(plab, store.DECK_PRIMARY_CHANNELS)
        plab2 = placement_menu.get()
        window_startup_placement = _placement_value_for.get(
            plab2, store.WINDOW_STARTUP_CENTER
        )
        d_anim_lab = drag_anim_menu.get()
        panel_drag_animation = _drag_anim_from_display.get(
            d_anim_lab, store.PANEL_DRAG_ANIM_NONE
        )
        return {
            "ui_theme": ui_theme,
            "ui_scale": ui_scale,
            "shortcuts": sd,
            "deck_cell_px": store.clamp_deck_cell_px(_deck_cell_px_from_ui()),
            "deck_show_hidden_items": bool(show_hidden_var.get()),
            "deck_primary_action": deck_primary_action,
            "window_startup_placement": window_startup_placement,
            "panel_drag_animation": panel_drag_animation,
            "always_on_top": bool(always_on_top_var.get()),
            "tile_mode": tile_mode[0],
            "tile_custom_text": cell_custom_entry.get().strip()
            if tile_mode[0] == "custom"
            else "",
        }

    last_applied: dict[str, object] = {}

    def _mark_dirty() -> None:
        a = last_applied
        w = _snapshot_from_widgets()
        dirty = (
            w["ui_theme"] != a["ui_theme"]
            or abs(float(w["ui_scale"]) - float(a["ui_scale"])) > 1e-6
            or w["shortcuts"] != a["shortcuts"]
            or int(w["deck_cell_px"]) != int(a["deck_cell_px"])
            or bool(w["deck_show_hidden_items"]) != bool(a["deck_show_hidden_items"])
            or w["deck_primary_action"] != a["deck_primary_action"]
            or w["window_startup_placement"] != a["window_startup_placement"]
            or w["panel_drag_animation"] != a["panel_drag_animation"]
            or bool(w["always_on_top"]) != bool(a["always_on_top"])
            or w["tile_mode"] != a["tile_mode"]
            or str(w.get("tile_custom_text", "")) != str(a.get("tile_custom_text", ""))
        )
        apply_btn.configure(state="normal" if dirty else "disabled")

    def _sync_last_applied_from_settings(
        s: store.AppSettings, always_on_top: bool
    ) -> None:
        px = store.clamp_deck_cell_px(s.deck_cell_px)
        if px in (25, 50, 75):
            tm = str(px)
            tc = ""
        else:
            tm = "custom"
            tc = str(px)
        last_applied.clear()
        last_applied.update(
            {
                "ui_theme": themes.clamp_theme_id(s.ui_theme),
                "ui_scale": store.clamp_ui_scale(s.ui_scale),
                "shortcuts": (
                    str(s.shortcuts_dir.resolve())
                    if s.shortcuts_dir is not None
                    else None
                ),
                "grid_cols": store.clamp_grid_cols(s.grid_cols),
                "deck_cell_px": px,
                "deck_show_hidden_items": s.deck_show_hidden_items,
                "deck_primary_action": s.deck_primary_action,
                "window_startup_placement": s.window_startup_placement,
                "panel_drag_animation": s.panel_drag_animation,
                "always_on_top": always_on_top,
                "tile_mode": tm,
                "tile_custom_text": tc,
            }
        )

    def reset_to_defaults() -> None:
        if not confirm_dialog(
            win,
            "Reset settings",
            "Reset every preference in this dialog to its factory defaults? "
            "Your database and shortcut files are not deleted.",
            confirm_text="Reset",
        ):
            return
        d = store.default_app_settings()
        c2 = store.connect()
        try:
            store.save_app_settings(c2, d)
            store.set_panel_always_on_top(c2, False)
        finally:
            c2.close()
        if on_saved is not None:
            on_saved(d)
        if on_always_on_top_changed is not None:
            on_always_on_top_changed(False)
        theme_menu.set(themes.THEME_LABELS[themes.clamp_theme_id(d.ui_theme)])
        nearest_d = store.nearest_ui_scale_preset_value(d.ui_scale)
        scale_lbl_d = next(
            lbl for lbl, v in store.UI_SCALE_PRESETS if v == nearest_d
        )
        scale_menu.set(scale_lbl_d)
        path_entry.delete(0, "end")
        px_d = store.clamp_deck_cell_px(d.deck_cell_px)
        if px_d in (25, 50, 75):
            tile_mode[0] = str(px_d)
            cell_custom_entry.configure(state="disabled")
            cell_custom_entry.delete(0, "end")
        else:
            tile_mode[0] = "custom"
            cell_custom_entry.configure(state="normal")
            cell_custom_entry.delete(0, "end")
            cell_custom_entry.insert(0, str(px_d))
        _sync_tile_buttons()
        show_hidden_var.set(d.deck_show_hidden_items)
        primary_menu.set(
            _primary_label_for.get(d.deck_primary_action, _primary_labels[0])
        )
        placement_menu.set(
            _placement_label_for.get(
                d.window_startup_placement, _placement_labels[0]
            )
        )
        always_on_top_var.set(False)
        drag_anim_menu.set(
            _drag_anim_display_for.get(d.panel_drag_animation, "None")
        )
        diag_body2 = _diagnostics_block(d)
        diag_box.configure(state="normal")
        diag_box.delete("1.0", "end")
        diag_box.insert("1.0", diag_body2)
        diag_box.configure(state="disabled")
        _sync_last_applied_from_settings(d, False)
        _mark_dirty()
        _stub_dialog(win, "Settings reset", "All preferences were restored to defaults.")

    btn_row = ctk.CTkFrame(outer, fg_color="transparent")
    btn_row.pack(fill="x", pady=(16, 0))

    def dismiss() -> None:
        try:
            win.grab_release()
        except Exception:
            pass
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", dismiss)
    win.bind("<Escape>", lambda _e: dismiss())

    def apply_changes() -> None:
        raw_path = _path_str_norm()
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

        scale_label = scale_menu.get()
        ui_scale = preset_by_label.get(scale_label, store.UI_SCALE_DEFAULT)
        ui_scale = store.clamp_ui_scale(ui_scale)

        plab = primary_menu.get()
        deck_primary_action = _primary_action_for.get(plab, store.DECK_PRIMARY_CHANNELS)

        theme_label = theme_menu.get()
        ui_theme = label_to_theme.get(theme_label, themes.default_theme_id())
        appearance_mode = themes.theme_appearance(ui_theme)

        deck_cell_px = store.clamp_deck_cell_px(_deck_cell_px_from_ui())

        plab2 = placement_menu.get()
        window_startup_placement = _placement_value_for.get(
            plab2, store.WINDOW_STARTUP_CENTER
        )

        d_anim_lab = drag_anim_menu.get()
        panel_drag_animation = _drag_anim_from_display.get(
            d_anim_lab, store.PANEL_DRAG_ANIM_NONE
        )
        always_on_top = bool(always_on_top_var.get())

        settings = store.AppSettings(
            appearance_mode=appearance_mode,
            ui_theme=ui_theme,
            shortcuts_dir=shortcuts_dir,
            grid_cols=int(last_applied["grid_cols"]),
            deck_cell_px=deck_cell_px,
            deck_show_hidden_items=bool(show_hidden_var.get()),
            ui_scale=ui_scale,
            deck_primary_action=deck_primary_action,
            window_startup_placement=window_startup_placement,
            panel_drag_animation=panel_drag_animation,
        )
        c2 = store.connect()
        try:
            store.save_app_settings(c2, settings)
            store.set_panel_always_on_top(c2, always_on_top)
        finally:
            c2.close()
        if on_always_on_top_changed is not None:
            on_always_on_top_changed(always_on_top)
        if on_saved is not None:
            on_saved(settings)
        _sync_last_applied_from_settings(settings, always_on_top)
        _mark_dirty()

    ctk.CTkButton(
        btn_row,
        text="Reset to defaults…",
        command=reset_to_defaults,
        width=140,
    ).pack(side="left")
    right_btns = ctk.CTkFrame(btn_row, fg_color="transparent")
    right_btns.pack(side="right")
    apply_btn = ctk.CTkButton(
        right_btns,
        text="Apply changes",
        command=apply_changes,
        width=120,
    )
    apply_btn.pack(side="right")
    ctk.CTkButton(right_btns, text="Cancel", command=dismiss, width=100).pack(
        side="right", padx=(0, 8)
    )

    def _wire_dirty() -> None:
        theme_menu.configure(command=lambda _v: _mark_dirty())
        scale_menu.configure(command=lambda _v: _mark_dirty())
        placement_menu.configure(command=lambda _v: _mark_dirty())
        primary_menu.configure(command=lambda _v: _mark_dirty())
        drag_anim_menu.configure(command=lambda _v: _mark_dirty())
        path_entry.bind("<KeyRelease>", lambda _e: _mark_dirty())
        cell_custom_entry.bind("<KeyRelease>", lambda _e: _mark_dirty())

        def _tb(*_a: object) -> None:
            _mark_dirty()

        show_hidden_var.trace_add("write", _tb)
        always_on_top_var.trace_add("write", _tb)

    _sync_last_applied_from_settings(current, shell.always_on_top)
    _wire_dirty()
    _mark_dirty()

    win.after_idle(lambda: theme_menu.focus_set())
