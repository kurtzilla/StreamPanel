"""Custom window chrome: borderless shell, drag strip, Pin / Settings / Close."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

import customtkinter as ctk

from streampanel import themes

STRIP_HEIGHT = 36
_MONITOR_SEG_MAX = 6


class _ChromeRefs(TypedDict, total=False):
    strip: ctk.CTkFrame
    btn_row: ctk.CTkFrame
    body: ctk.CTkFrame
    drag_frame: ctk.CTkFrame
    grip_frame: ctk.CTkFrame
    grip_label: ctk.CTkLabel
    strip_ghost_buttons: list[ctk.CTkButton]
    close_btn: ctk.CTkButton
    drag_label: ctk.CTkLabel
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
) -> None:
    drag_attr = "_streampanel_drag_xy"

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
    for w in (d["strip"], d["btn_row"], d["drag_frame"]):
        w.configure(fg_color=p.strip_bg)
    gf = d.get("grip_frame")
    if gf is not None:
        gf.configure(fg_color=p.strip_bg, border_color=p.strip_button_hover)
    gl = d.get("grip_label")
    if gl is not None:
        gl.configure(text_color=p.drag_hint_text)
    d["body"].configure(fg_color=p.shell_bg)
    for b in d["strip_ghost_buttons"]:
        b.configure(hover_color=p.strip_button_hover)
    d["close_btn"].configure(fg_color=p.close_fg, hover_color=p.close_hover)
    d["drag_label"].configure(text_color=p.drag_hint_text)
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


def apply_borderless_chrome(
    root: ctk.CTk,
    *,
    always_on_top: bool = False,
    on_pin_toggled: object | None = None,
    on_settings: object | None = None,
    on_close: object | None = None,
    top_rail_snap: Callable[[int, int, int, int, int], tuple[int, int]] | None = None,
    monitor_values: list[str] | None = None,
    on_monitor_selected: Callable[[str], None] | None = None,
) -> ctk.CTkFrame:
    """
    Remove native title bar and add top strip: drag grip, hint, Pin, Settings, Close.

    Optional ``monitor_*`` uses small ``CTkButton`` labels (no ``Menu.post``).
    ``top_rail_snap`` pins the strip drag to the top work edge.

    Returns a ``CTkFrame`` packed below the strip for main content.
    """
    p = themes.current_palette()
    root.overrideredirect(True)
    root.configure(fg_color=p.shell_bg)
    root.attributes("-topmost", always_on_top)

    strip = ctk.CTkFrame(root, fg_color=p.strip_bg, corner_radius=0, height=STRIP_HEIGHT)
    strip.pack(fill="x", side="top")
    strip.pack_propagate(False)

    btn_row = ctk.CTkFrame(strip, fg_color=p.strip_bg, corner_radius=0)
    btn_row.pack(side="right", fill="y", padx=(0, 8), pady=4)

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

    pin_on = always_on_top

    def pin_cb() -> None:
        nonlocal pin_on
        pin_on = not pin_on
        root.attributes("-topmost", pin_on)
        pin_btn.configure(text="Pin on" if pin_on else "Pin off")
        if callable(on_pin_toggled):
            on_pin_toggled(pin_on)

    ghost = dict(
        corner_radius=6,
        fg_color="transparent",
        hover_color=p.strip_button_hover,
        font=ctk.CTkFont(size=12),
        height=26,
    )
    pin_btn = ctk.CTkButton(
        btn_row,
        text="Pin on" if pin_on else "Pin off",
        command=pin_cb,
        width=64,
        **ghost,
    )
    pin_btn.pack(side="left", padx=(4, 0))
    settings_btn = ctk.CTkButton(
        btn_row,
        text="Settings",
        command=settings_cb,
        width=80,
        **ghost,
    )
    settings_btn.pack(side="left", padx=(4, 0))
    close_btn = ctk.CTkButton(
        btn_row,
        text="×",
        command=close_cb,
        width=30,
        height=26,
        corner_radius=4,
        fg_color=p.close_fg,
        hover_color=p.close_hover,
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    close_btn.pack(side="left", padx=(8, 0))

    strip_ghosts: list[ctk.CTkButton] = [pin_btn, settings_btn]
    monitor_buttons: list[ctk.CTkButton] = []
    monitor_overflow_btn: ctk.CTkButton | None = None
    if (
        monitor_values
        and len(monitor_values) > 1
        and callable(on_monitor_selected)
    ):
        if len(monitor_values) <= _MONITOR_SEG_MAX:
            host = ctk.CTkFrame(strip, fg_color="transparent")
            host.pack(side="left", padx=(8, 0), pady=4)
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
                strip,
                text="Displays…",
                command=overflow_cb,
                width=88,
                **ghost,
            )
            monitor_overflow_btn.pack(side="left", padx=(8, 0), pady=4)
            strip_ghosts.append(monitor_overflow_btn)

    drag = ctk.CTkFrame(strip, fg_color=p.strip_bg, corner_radius=0)
    drag.pack(side="left", fill="both", expand=True, padx=(6, 4), pady=4)

    grip = ctk.CTkFrame(
        drag,
        fg_color=p.strip_bg,
        corner_radius=4,
        width=36,
        height=26,
        border_width=1,
        border_color=p.strip_button_hover,
    )
    grip.pack(side="left", padx=(0, 8), pady=0)
    grip.pack_propagate(False)
    grip_lbl = ctk.CTkLabel(
        grip,
        text="⋮⋮",
        font=ctk.CTkFont(size=14),
        text_color=p.drag_hint_text,
    )
    grip_lbl.place(relx=0.5, rely=0.5, anchor="center")
    try:
        grip.configure(cursor="fleur")
        grip_lbl.configure(cursor="fleur")
    except Exception:
        pass
    _bind_drag_region(grip, root, top_rail_snap=top_rail_snap)
    _bind_drag_region(grip_lbl, root, top_rail_snap=top_rail_snap)

    drag_label = ctk.CTkLabel(
        drag,
        text="StreamPanel — drag along top / between displays",
        font=ctk.CTkFont(size=12),
        text_color=p.drag_hint_text,
        anchor="w",
    )
    drag_label.pack(side="left", fill="x", expand=True)
    _bind_drag_region(drag_label, root, top_rail_snap=top_rail_snap)

    body = ctk.CTkFrame(root, fg_color=p.shell_bg, corner_radius=0)
    body.pack(fill="both", expand=True)

    refs: _ChromeRefs = {
        "strip": strip,
        "btn_row": btn_row,
        "body": body,
        "drag_frame": drag,
        "grip_frame": grip,
        "grip_label": grip_lbl,
        "strip_ghost_buttons": strip_ghosts,
        "close_btn": close_btn,
        "drag_label": drag_label,
    }
    if monitor_buttons:
        refs["monitor_buttons"] = monitor_buttons
    if monitor_overflow_btn is not None:
        refs["monitor_overflow_btn"] = monitor_overflow_btn
    setattr(root, "_streampanel_chrome", refs)
    return body
