"""Custom window chrome: borderless shell, drag strip, gear Settings / Close."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import TypedDict

import customtkinter as ctk

from streampanel import themes

# Must match ``streampanel.store.PANEL_DRAG_ANIM_*`` (do not import ``store`` here:
# ``store`` → ``panel_layout`` → this module → circular import).
PANEL_DRAG_ANIM_NONE = "none"
PANEL_DRAG_ANIM_FADE = "fade"
PANEL_DRAG_ANIM_SLIDE = "slide"

STRIP_HEIGHT = 36
_MONITOR_SEG_MAX = 6

# Borderless shell: rounded client chrome (strip + body); Windows 11 also
# applies small HWND rounding via ``win_overlay.apply_dwm_rounded_corners``.
SHELL_CORNER_RADIUS = 12


class _ChromeRefs(TypedDict, total=False):
    strip: ctk.CTkFrame
    right_row: ctk.CTkFrame
    body: ctk.CTkFrame
    drag_frame: ctk.CTkFrame
    title_bar: ctk.CTkFrame
    move_icon: ctk.CTkLabel
    title_label: ctk.CTkLabel
    strip_ghost_buttons: list[ctk.CTkButton]
    close_btn: ctk.CTkButton
    settings_btn: ctk.CTkButton
    drawer_collapse_btn: ctk.CTkButton
    monitor_buttons: list[ctk.CTkButton]
    monitor_overflow_btn: ctk.CTkButton


def _stub_dialog(parent: ctk.CTk, title: str, message: str) -> None:
    win = ctk.CTkToplevel(parent)
    win.title(title)
    win.geometry("340x120")
    win.transient(parent)
    win.configure(fg_color=themes.dialog_background())
    win.attributes("-topmost", True)
    win.after(100, lambda: win.attributes("-topmost", False))
    frame = ctk.CTkFrame(win, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=16, pady=16)
    ctk.CTkLabel(frame, text=message, wraplength=300).pack(pady=(0, 12))

    def dismiss() -> None:
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", dismiss)
    win.bind("<Escape>", lambda _e: dismiss())
    ctk.CTkButton(frame, text="OK", command=dismiss, width=80).pack()


PANEL_DRAG_STATE_ATTR = "_streampanel_panel_drag_state"

_PANEL_DRAG_ANIM_VALID = frozenset(
    {PANEL_DRAG_ANIM_NONE, PANEL_DRAG_ANIM_FADE, PANEL_DRAG_ANIM_SLIDE}
)


def _resolve_anim_style(
    get_style: Callable[[], str] | None,
    *,
    default: str = PANEL_DRAG_ANIM_NONE,
) -> str:
    if get_style is None:
        return default
    try:
        s = str(get_style()).strip().lower()
    except Exception:
        return default
    if s in _PANEL_DRAG_ANIM_VALID:
        return s
    return default


def attach_tooltip(
    widget: ctk.CTkButton | ctk.CTkLabel | ctk.CTkFrame,
    text: str,
    *,
    delay_ms: int = 500,
) -> None:
    """Small hover tooltip; does not grab focus."""
    tip_ref: list[ctk.CTkToplevel | None] = [None]
    after_ref: list[str | int | None] = [None]

    def cancel_scheduled() -> None:
        aid = after_ref[0]
        if aid is not None:
            try:
                widget.after_cancel(aid)
            except Exception:
                pass
            after_ref[0] = None

    def hide_tip() -> None:
        cancel_scheduled()
        tw = tip_ref[0]
        if tw is not None:
            try:
                tw.destroy()
            except Exception:
                pass
            tip_ref[0] = None

    def show_tip() -> None:
        after_ref[0] = None
        try:
            if not widget.winfo_exists():
                return
        except Exception:
            return
        p = themes.current_palette()
        top = widget.winfo_toplevel()
        tw = ctk.CTkToplevel(top)
        tw.overrideredirect(True)
        tw.attributes("-topmost", True)
        tw.configure(fg_color=p.shell_bg)
        lbl = ctk.CTkLabel(
            tw,
            text=text,
            font=ctk.CTkFont(size=12),
            text_color=p.drag_hint_text,
            corner_radius=4,
            fg_color=p.shell_bg,
            border_width=1,
            border_color=p.strip_button_hover,
            padx=8,
            pady=4,
        )
        lbl.pack()
        tw.update_idletasks()
        tw_w = int(tw.winfo_reqwidth())
        tw_h = int(tw.winfo_reqheight())
        rx = int(widget.winfo_rootx())
        ry = int(widget.winfo_rooty()) + int(widget.winfo_height()) + 4
        tw.geometry(f"{tw_w}x{tw_h}+{rx}+{ry}")
        tip_ref[0] = tw

    def on_enter(_event: object) -> None:
        hide_tip()

        def schedule() -> None:
            after_ref[0] = widget.after(delay_ms, show_tip)

        schedule()

    def on_leave(_event: object) -> None:
        hide_tip()

    def on_press(_event: object) -> None:
        hide_tip()

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)
    widget.bind("<ButtonPress-1>", on_press)
    widget.bind("<Destroy>", lambda _e: hide_tip())


def compute_drag_rect(
    origin_xy: tuple[int, int],
    size_wh: tuple[int, int],
    e_x_root: int,
    e_y_root: int,
    *,
    pointer_x: int,
    top_rail_snap: Callable[[int, int, int, int, int], tuple[int, int]] | None,
) -> tuple[int, int, int, int]:
    """
    Pure helper: window (w, h) and top-left (x, y) from drag origin and pointer.

    ``pointer_x`` is passed to ``top_rail_snap`` as the first argument when set.
    """
    ox, oy = origin_xy
    w, h = size_wh
    x = int(e_x_root) - ox
    y = int(e_y_root) - oy
    if top_rail_snap is not None:
        x, y = top_rail_snap(int(pointer_x), x, y, w, h)
    return w, h, x, y


def _create_placement_ghost(
    parent: ctk.CTk,
    w: int,
    h: int,
    x: int,
    y: int,
) -> ctk.CTkToplevel:
    """Translucent outline window for drag placement preview (no deck content)."""
    p = themes.current_palette()
    ghost = ctk.CTkToplevel(parent)
    ghost.overrideredirect(True)
    ghost.attributes("-topmost", True)
    try:
        ghost.attributes("-alpha", 0.55)
    except Exception:
        pass
    try:
        ghost.attributes("-disabled", True)
    except Exception:
        pass
    ghost.configure(fg_color="transparent")
    inner = ctk.CTkFrame(
        ghost,
        fg_color=p.ghost_cell,
        corner_radius=SHELL_CORNER_RADIUS,
        border_width=2,
        border_color=p.strip_button_hover,
    )
    inner.pack(fill="both", expand=True)
    ghost.geometry(f"{w}x{h}+{x}+{y}")
    return ghost


def confirm_dialog(parent: ctk.CTk, title: str, message: str, *, confirm_text: str = "Launch") -> bool:
    """Modal OK/Cancel-style dialog; returns True if the user chose *confirm_text*."""
    accepted: list[bool] = [False]
    win = ctk.CTkToplevel(parent)
    win.title(title)
    win.geometry("380x140")
    win.minsize(340, 120)
    win.transient(parent)
    win.configure(fg_color=themes.dialog_background())
    win.attributes("-topmost", True)
    win.after(100, lambda: win.attributes("-topmost", False))
    win.grab_set()

    frame = ctk.CTkFrame(win, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=16, pady=16)
    ctk.CTkLabel(frame, text=message, wraplength=340, justify="left").pack(
        fill="x", pady=(0, 12)
    )
    row = ctk.CTkFrame(frame, fg_color="transparent")
    row.pack(fill="x")

    def on_cancel() -> None:
        try:
            win.grab_release()
        except Exception:
            pass
        win.destroy()

    def on_confirm() -> None:
        accepted[0] = True
        on_cancel()

    win.protocol("WM_DELETE_WINDOW", on_cancel)

    ctk.CTkButton(row, text=confirm_text, command=on_confirm, width=100).pack(side="right")
    ctk.CTkButton(row, text="Cancel", command=on_cancel, width=100).pack(side="right", padx=(0, 8))

    win.bind("<Escape>", lambda _e: on_cancel())

    parent.wait_window(win)
    return accepted[0]


def _bind_drag_region(
    widget: ctk.CTkFrame | ctk.CTkLabel,
    root: ctk.CTk,
    *,
    top_rail_snap: Callable[[int, int, int, int, int], tuple[int, int]] | None = None,
    on_drag_start: Callable[[], None] | None = None,
    on_drag_end: Callable[[], None] | None = None,
    get_drag_animation: Callable[[], str] | None = None,
    get_drag_ghost_wh: Callable[[], tuple[int, int]] | None = None,
) -> None:
    drag_attr = "_streampanel_drag_xy"

    if on_drag_start is None or on_drag_end is None:
        def start_move(event: object) -> None:
            e = event  # type: ignore[assignment]
            setattr(
                root,
                drag_attr,
                (e.x_root - root.winfo_x(), e.y_root - root.winfo_y()),
            )

        def on_motion(event: object) -> None:
            origin = getattr(root, drag_attr, None)
            if origin is None:
                return
            e = event  # type: ignore[assignment]
            ox, oy = origin
            x = e.x_root - ox
            y = e.y_root - oy
            w, h = root.winfo_width(), root.winfo_height()
            if top_rail_snap is not None:
                x, y = top_rail_snap(int(e.x_root), x, y, w, h)
            root.geometry(f"{w}x{h}+{x}+{y}")

        widget.bind("<ButtonPress-1>", start_move)
        widget.bind("<B1-Motion>", on_motion)
        return

    _drag_instrument_attr = "_streampanel_panel_drag_instrumented"
    _ANIM_MS = 160
    _ANIM_STEP = 16

    def _get_drag_state() -> dict[str, object] | None:
        raw = getattr(root, PANEL_DRAG_STATE_ATTR, None)
        return raw if isinstance(raw, dict) else None

    def _clear_drag_state() -> None:
        try:
            delattr(root, PANEL_DRAG_STATE_ATTR)
        except AttributeError:
            pass

    def _finish_panel_drag(*, apply_position: bool) -> None:
        st = _get_drag_state()
        if st is None:
            return
        ghost = st.get("ghost")
        wh = st.get("wh")
        w, h = (int(wh[0]), int(wh[1])) if isinstance(wh, tuple) and len(wh) == 2 else (1, 1)
        gx: int | None = None
        gy: int | None = None
        if apply_position and ghost is not None:
            try:
                if ghost.winfo_exists():
                    gx = int(ghost.winfo_x())
                    gy = int(ghost.winfo_y())
            except Exception:
                pass
        if ghost is not None:
            try:
                ghost.destroy()
            except Exception:
                pass
        _clear_drag_state()
        try:
            root.unbind("<Escape>")
        except Exception:
            pass

        if not apply_position:
            on_drag_end()
            return
        if gx is None or gy is None:
            on_drag_end()
            return

        style = _resolve_anim_style(get_drag_animation)

        def _call_end() -> None:
            on_drag_end()

        if style == PANEL_DRAG_ANIM_NONE:
            root.geometry(f"{w}x{h}+{gx}+{gy}")
            _call_end()
            return

        if style == PANEL_DRAG_ANIM_FADE:
            try:
                prev_alpha = float(root.attributes("-alpha"))
            except Exception:
                prev_alpha = 1.0
            try:
                root.attributes("-alpha", 0.0)
            except Exception:
                root.geometry(f"{w}x{h}+{gx}+{gy}")
                _call_end()
                return
            root.geometry(f"{w}x{h}+{gx}+{gy}")
            try:
                root.update_idletasks()
            except Exception:
                pass
            n = max(1, (_ANIM_MS + _ANIM_STEP - 1) // _ANIM_STEP)

            def fade_step(i: int) -> None:
                try:
                    if not root.winfo_exists():
                        _call_end()
                        return
                except Exception:
                    _call_end()
                    return
                if i >= n:
                    try:
                        root.attributes("-alpha", prev_alpha)
                    except Exception:
                        pass
                    _call_end()
                    return
                t = (i + 1) / n
                try:
                    root.attributes("-alpha", prev_alpha * t)
                except Exception:
                    _call_end()
                    return
                root.after(_ANIM_STEP, lambda: fade_step(i + 1))

            root.after(0, lambda: fade_step(0))
            return

        if style == PANEL_DRAG_ANIM_SLIDE:
            try:
                sx = int(root.winfo_x())
                sy = int(root.winfo_y())
            except Exception:
                sx, sy = gx, gy
            n = max(1, (_ANIM_MS + _ANIM_STEP - 1) // _ANIM_STEP)

            def slide_step(i: int) -> None:
                try:
                    if not root.winfo_exists():
                        _call_end()
                        return
                except Exception:
                    _call_end()
                    return
                if i >= n:
                    root.geometry(f"{w}x{h}+{gx}+{gy}")
                    _call_end()
                    return
                t = (i + 1) / n
                x = int(sx + (gx - sx) * t)
                y = int(sy + (gy - sy) * t)
                root.geometry(f"{w}x{h}+{x}+{y}")
                root.after(_ANIM_STEP, lambda: slide_step(i + 1))

            root.after(0, lambda: slide_step(0))
            return

        root.geometry(f"{w}x{h}+{gx}+{gy}")
        _call_end()

    def _ghost_only_teardown() -> None:
        st = _get_drag_state()
        if st is None:
            return
        ghost = st.get("ghost")
        if ghost is not None:
            try:
                ghost.destroy()
            except Exception:
                pass
        _clear_drag_state()
        try:
            root.unbind("<Escape>")
        except Exception:
            pass

    def _register_root_drag_helpers_once() -> None:
        if getattr(root, _drag_instrument_attr, False):
            return
        setattr(root, _drag_instrument_attr, True)

        def on_root_destroy(event: object) -> None:
            ev = event  # type: ignore[assignment]
            if ev.widget is not root:
                return
            _ghost_only_teardown()

        def on_root_focus_out_drag(_event: object) -> None:
            if _get_drag_state() is None:
                return

            def deferred() -> None:
                st = _get_drag_state()
                if st is None:
                    return
                ghost_win = st.get("ghost")
                try:
                    wfocus = root.focus_get()
                except Exception:
                    wfocus = None
                if wfocus is None:
                    _finish_panel_drag(apply_position=False)
                    return
                try:
                    top = wfocus.winfo_toplevel()
                except Exception:
                    _finish_panel_drag(apply_position=False)
                    return
                if top is root:
                    return
                if ghost_win is not None and top is ghost_win:
                    return
                _finish_panel_drag(apply_position=False)

            root.after_idle(deferred)

        root.bind("<Destroy>", on_root_destroy, add="+")
        root.bind("<FocusOut>", on_root_focus_out_drag, add="+")

    def start_move(event: object) -> None:
        if _get_drag_state() is not None:
            return
        e = event  # type: ignore[assignment]
        root.update_idletasks()
        if get_drag_ghost_wh is not None:
            try:
                gw, gh = get_drag_ghost_wh()
                w, h = int(gw), int(gh)
            except Exception:
                w, h = int(root.winfo_width()), int(root.winfo_height())
        else:
            w, h = int(root.winfo_width()), int(root.winfo_height())
        rx, ry = int(root.winfo_x()), int(root.winfo_y())
        ox = int(e.x_root) - rx
        oy = int(e.y_root) - ry
        _register_root_drag_helpers_once()
        on_drag_start()
        ghost = _create_placement_ghost(root, w, h, rx, ry)
        setattr(
            root,
            PANEL_DRAG_STATE_ATTR,
            {"wh": (w, h), "origin": (ox, oy), "ghost": ghost},
        )

        def on_esc(_ev: object) -> str:
            _finish_panel_drag(apply_position=False)
            return "break"

        root.bind("<Escape>", on_esc)

    def on_motion(event: object) -> None:
        st = _get_drag_state()
        if st is None:
            return
        e = event  # type: ignore[assignment]
        origin = st.get("origin")
        wh = st.get("wh")
        ghost = st.get("ghost")
        if (
            not isinstance(origin, tuple)
            or len(origin) != 2
            or not isinstance(wh, tuple)
            or len(wh) != 2
            or ghost is None
        ):
            return
        w, h, x, y = compute_drag_rect(
            (int(origin[0]), int(origin[1])),
            (int(wh[0]), int(wh[1])),
            int(e.x_root),
            int(e.y_root),
            pointer_x=int(e.x_root),
            top_rail_snap=top_rail_snap,
        )
        try:
            if ghost.winfo_exists():
                ghost.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def on_release(_event: object) -> None:
        _finish_panel_drag(apply_position=True)

    widget.bind("<ButtonPress-1>", start_move)
    widget.bind("<B1-Motion>", on_motion)
    widget.bind("<ButtonRelease-1>", on_release)


def _open_monitor_overflow_picker(
    root: ctk.CTk,
    labels: list[str],
    on_select: Callable[[str], None],
) -> None:
    p = themes.current_palette()
    win = ctk.CTkToplevel(root)
    win.title("Choose display")
    win.transient(root)
    win.configure(fg_color=themes.dialog_background())
    win.attributes("-topmost", True)
    win.after(120, lambda: win.attributes("-topmost", False))
    h = min(520, 48 + len(labels) * 40)
    win.geometry(f"260x{h}")
    outer = ctk.CTkScrollableFrame(win, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=12, pady=12)

    def pick(label: str) -> None:
        on_select(label)
        win.destroy()

    for lb in labels:
        ctk.CTkButton(
            outer,
            text=lb,
            command=lambda l=lb: pick(l),
            height=32,
            anchor="w",
            fg_color=p.shell_bg,
            hover_color=p.strip_button_hover,
            font=ctk.CTkFont(size=13),
        ).pack(fill="x", pady=(0, 6))

    win.protocol("WM_DELETE_WINDOW", win.destroy)
    win.bind("<Escape>", lambda _e: win.destroy())


def refresh_chrome_theme(root: ctk.CTk) -> None:
    raw = getattr(root, "_streampanel_chrome", None)
    if not isinstance(raw, dict):
        return
    d: _ChromeRefs = raw  # type: ignore[assignment]
    p = themes.current_palette()
    root.configure(fg_color=p.shell_bg)
    d["strip"].configure(
        fg_color=p.strip_bg,
        background_corner_colors=(
            p.strip_bg,
            p.strip_bg,
            p.shell_bg,
            p.shell_bg,
        ),
    )
    for w in (d["right_row"], d["drag_frame"], d.get("title_bar")):
        if w is not None:
            w.configure(fg_color=p.strip_bg)
    mi = d.get("move_icon")
    if mi is not None:
        mi.configure(text_color=p.drag_hint_text)
    tl = d.get("title_label")
    if tl is not None:
        tl.configure(text_color=p.drag_hint_text)
    d["body"].configure(fg_color=p.shell_bg)
    for b in d["strip_ghost_buttons"]:
        b.configure(hover_color=p.strip_button_hover)
    d["close_btn"].configure(fg_color=p.close_fg, hover_color=p.close_hover)
    sb = d.get("settings_btn")
    if sb is not None:
        sb.configure(
            fg_color="transparent",
            hover_color=p.strip_button_hover,
            text_color=p.drag_hint_text,
        )
    for b in d.get("monitor_buttons") or []:
        b.configure(
            fg_color="transparent",
            hover_color=p.strip_button_hover,
            text_color=p.drag_hint_text,
        )
    mob = d.get("monitor_overflow_btn")
    if mob is not None:
        mob.configure(
            fg_color="transparent",
            hover_color=p.strip_button_hover,
            text_color=p.drag_hint_text,
        )
    dcb = d.get("drawer_collapse_btn")
    if dcb is not None:
        dcb.configure(
            fg_color="transparent",
            hover_color=p.strip_button_hover,
            text_color=p.drag_hint_text,
        )


def apply_borderless_chrome(
    root: ctk.CTk,
    *,
    always_on_top: bool = False,
    on_settings: object | None = None,
    on_close: object | None = None,
    top_rail_snap: Callable[[int, int, int, int, int], tuple[int, int]] | None = None,
    monitor_values: list[str] | None = None,
    on_monitor_selected: Callable[[str], None] | None = None,
    on_panel_drag_start: Callable[[], None] | None = None,
    on_panel_drag_end: Callable[[], None] | None = None,
    get_drag_animation: Callable[[], str] | None = None,
    get_drag_ghost_wh: Callable[[], tuple[int, int]] | None = None,
    on_drawer_collapse: Callable[[], None] | None = None,
) -> ctk.CTkFrame:
    """
    Remove native title bar and add top strip: move icon + title (drag), optional
    display picker, gear (Settings), Close.

    Optional ``monitor_*`` uses small ``CTkButton`` labels (no ``Menu.post``).
    ``top_rail_snap`` pins the strip drag to the top work edge.
    When ``on_panel_drag_start`` and ``on_panel_drag_end`` are both set, strip
    dragging uses a ghost preview toplevel and defers moving the root until release.

    Returns a ``CTkFrame`` packed below the strip for main content.
    """
    p = themes.current_palette()
    root.overrideredirect(True)
    root.configure(fg_color=p.shell_bg)
    root.attributes("-topmost", always_on_top)

    strip_corner_fill = (
        p.strip_bg,
        p.strip_bg,
        p.shell_bg,
        p.shell_bg,
    )
    strip = ctk.CTkFrame(
        root,
        fg_color=p.strip_bg,
        corner_radius=SHELL_CORNER_RADIUS,
        height=STRIP_HEIGHT,
        background_corner_colors=strip_corner_fill,
    )
    strip.pack(fill="x", side="top")
    strip.pack_propagate(False)

    right_row = ctk.CTkFrame(strip, fg_color=p.strip_bg, corner_radius=0)
    right_row.pack(side="right", fill="y", padx=(0, 8), pady=4)

    monitor_buttons: list[ctk.CTkButton] = []
    monitor_overflow_btn: ctk.CTkButton | None = None
    strip_ghosts: list[ctk.CTkButton] = []

    drawer_collapse_btn: ctk.CTkButton | None = None
    if callable(on_drawer_collapse):

        def _drawer_collapse_cb() -> None:
            on_drawer_collapse()

        drawer_collapse_btn = ctk.CTkButton(
            right_row,
            text="⌄",
            command=_drawer_collapse_cb,
            width=28,
            height=26,
            corner_radius=6,
            fg_color="transparent",
            hover_color=p.strip_button_hover,
            font=ctk.CTkFont(size=14),
        )
        drawer_collapse_btn.pack(side="left", padx=(0, 6), pady=0)
        strip_ghosts.append(drawer_collapse_btn)
        attach_tooltip(drawer_collapse_btn, "Hide deck")

    def settings_cb() -> None:
        if callable(on_settings):
            on_settings()
        else:
            _stub_dialog(root, "Settings", "Settings UI comes in a later slice (settings-window-ui).")

    def close_cb() -> None:
        if callable(on_close):
            on_close()
        else:
            root.destroy()

    ghost_btn = dict(
        corner_radius=6,
        fg_color="transparent",
        hover_color=p.strip_button_hover,
        font=ctk.CTkFont(size=12),
        height=26,
    )
    gear_font = (
        ctk.CTkFont(family="Segoe UI Symbol", size=15)
        if sys.platform == "win32"
        else ctk.CTkFont(size=15)
    )

    if (
        monitor_values
        and len(monitor_values) > 1
        and callable(on_monitor_selected)
    ):
        if len(monitor_values) <= _MONITOR_SEG_MAX:
            host = ctk.CTkFrame(right_row, fg_color="transparent")
            host.pack(side="left", padx=(0, 6), pady=0)
            for i in range(len(monitor_values)):
                lab = str(i + 1)
                mb = ctk.CTkButton(
                    host,
                    text=lab,
                    command=lambda s=lab: on_monitor_selected(s),
                    width=28,
                    height=26,
                    corner_radius=4,
                    font=ctk.CTkFont(size=12),
                    fg_color="transparent",
                    hover_color=p.strip_button_hover,
                    text_color=p.drag_hint_text,
                )
                mb.pack(side="left", padx=(0, 2))
                monitor_buttons.append(mb)
        else:

            def overflow_cb() -> None:
                if callable(on_monitor_selected):
                    _open_monitor_overflow_picker(root, monitor_values, on_monitor_selected)

            monitor_overflow_btn = ctk.CTkButton(
                right_row,
                text="Displays…",
                command=overflow_cb,
                width=88,
                **ghost_btn,
            )
            monitor_overflow_btn.pack(side="left", padx=(0, 6), pady=0)
            strip_ghosts.append(monitor_overflow_btn)

    settings_btn = ctk.CTkButton(
        right_row,
        text="⚙",
        command=settings_cb,
        width=32,
        height=26,
        corner_radius=6,
        fg_color="transparent",
        hover_color=p.strip_button_hover,
        font=gear_font,
    )
    settings_btn.pack(side="left", padx=(0, 6), pady=0)
    strip_ghosts.append(settings_btn)
    attach_tooltip(settings_btn, "Settings")

    close_btn = ctk.CTkButton(
        right_row,
        text="×",
        command=close_cb,
        width=30,
        height=26,
        corner_radius=4,
        fg_color=p.close_fg,
        hover_color=p.close_hover,
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    close_btn.pack(side="left", padx=(0, 0), pady=0)

    title_bar = ctk.CTkFrame(strip, fg_color=p.strip_bg, corner_radius=0)
    title_bar.pack(side="left", padx=(8, 4), pady=4)
    move_font = (
        ctk.CTkFont(family="Segoe UI Symbol", size=14)
        if sys.platform == "win32"
        else ctk.CTkFont(size=14)
    )
    move_icon = ctk.CTkLabel(
        title_bar,
        text="✥",
        font=move_font,
        text_color=p.drag_hint_text,
    )
    title_label = ctk.CTkLabel(
        title_bar,
        text="StreamPanel",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color=p.drag_hint_text,
        anchor="w",
    )
    move_icon.pack(side="left", padx=(0, 6), pady=0)
    title_label.pack(side="left", pady=0)
    for w in (move_icon, title_label):
        try:
            w.configure(cursor="fleur")
        except Exception:
            pass

    drag = ctk.CTkFrame(strip, fg_color=p.strip_bg, corner_radius=0)
    drag.pack(side="left", fill="both", expand=True, padx=(0, 4), pady=4)
    try:
        drag.configure(cursor="fleur")
    except Exception:
        pass

    _drag_kw: dict[str, object] = {
        "top_rail_snap": top_rail_snap,
        "get_drag_animation": get_drag_animation,
        "get_drag_ghost_wh": get_drag_ghost_wh,
    }
    if on_panel_drag_start is not None and on_panel_drag_end is not None:
        _drag_kw["on_drag_start"] = on_panel_drag_start
        _drag_kw["on_drag_end"] = on_panel_drag_end
    _bind_drag_region(move_icon, root, **_drag_kw)
    _bind_drag_region(title_label, root, **_drag_kw)
    _bind_drag_region(drag, root, **_drag_kw)

    body = ctk.CTkFrame(
        root,
        fg_color=p.shell_bg,
        corner_radius=SHELL_CORNER_RADIUS,
    )
    body.pack(fill="both", expand=True)

    refs: _ChromeRefs = {
        "strip": strip,
        "right_row": right_row,
        "body": body,
        "drag_frame": drag,
        "title_bar": title_bar,
        "move_icon": move_icon,
        "title_label": title_label,
        "strip_ghost_buttons": strip_ghosts,
        "close_btn": close_btn,
        "settings_btn": settings_btn,
    }
    if drawer_collapse_btn is not None:
        refs["drawer_collapse_btn"] = drawer_collapse_btn
    if monitor_buttons:
        refs["monitor_buttons"] = monitor_buttons
    if monitor_overflow_btn is not None:
        refs["monitor_overflow_btn"] = monitor_overflow_btn
    setattr(root, "_streampanel_chrome", refs)
    return body
