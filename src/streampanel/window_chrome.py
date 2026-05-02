"""Custom window chrome: borderless shell, drag strip, Settings / Add link / Close."""

from __future__ import annotations

import customtkinter as ctk

# Charcoal shell (plan: ~#1e1e1e / #252526)
COLOR_BG = "#1e1e1e"
COLOR_STRIP = "#252526"
COLOR_ACCENT_HOVER = "#3d3d3d"
STRIP_HEIGHT = 36


def _stub_dialog(parent: ctk.CTk, title: str, message: str) -> None:
    win = ctk.CTkToplevel(parent)
    win.title(title)
    win.geometry("340x120")
    win.transient(parent)
    win.attributes("-topmost", True)
    win.after(100, lambda: win.attributes("-topmost", False))
    frame = ctk.CTkFrame(win, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=16, pady=16)
    ctk.CTkLabel(frame, text=message, wraplength=300).pack(pady=(0, 12))
    ctk.CTkButton(frame, text="OK", command=win.destroy, width=80).pack()


def confirm_dialog(parent: ctk.CTk, title: str, message: str, *, confirm_text: str = "Launch") -> bool:
    """Modal OK/Cancel-style dialog; returns True if the user chose *confirm_text*."""
    accepted: list[bool] = [False]
    win = ctk.CTkToplevel(parent)
    win.title(title)
    win.geometry("380x140")
    win.minsize(340, 120)
    win.transient(parent)
    win.configure(fg_color=COLOR_BG)
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

    parent.wait_window(win)
    return accepted[0]


def _bind_drag_region(widget: ctk.CTkFrame, root: ctk.CTk) -> None:
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
        root.geometry(f"{root.winfo_width()}x{root.winfo_height()}+{x}+{y}")

    widget.bind("<ButtonPress-1>", start_move)
    widget.bind("<B1-Motion>", on_motion)


def apply_borderless_chrome(
    root: ctk.CTk,
    *,
    always_on_top: bool = False,
    on_pin_toggled: object | None = None,
    on_settings: object | None = None,
    on_add_link: object | None = None,
    on_close: object | None = None,
) -> ctk.CTkFrame:
    """
    Remove native title bar and add top strip: drag, Pin, Settings, Add link, Close.

    Returns a ``CTkFrame`` packed below the strip for main content.
    """
    root.overrideredirect(True)
    root.configure(fg_color=COLOR_BG)
    root.attributes("-topmost", always_on_top)

    strip = ctk.CTkFrame(root, fg_color=COLOR_STRIP, corner_radius=0, height=STRIP_HEIGHT)
    strip.pack(fill="x", side="top")
    strip.pack_propagate(False)

    btn_row = ctk.CTkFrame(strip, fg_color=COLOR_STRIP, corner_radius=0)
    btn_row.pack(side="right", fill="y", padx=(0, 8), pady=4)

    def settings_cb() -> None:
        if callable(on_settings):
            on_settings()
        else:
            _stub_dialog(root, "Settings", "Settings UI comes in a later slice (settings-window-ui).")

    def add_link_cb() -> None:
        if callable(on_add_link):
            on_add_link()
        else:
            _stub_dialog(root, "Add link", "Add-link dialog comes in add-link-ux.")

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
        hover_color=COLOR_ACCENT_HOVER,
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
    ctk.CTkButton(
        btn_row,
        text="Settings",
        command=settings_cb,
        width=80,
        **ghost,
    ).pack(side="left", padx=(4, 0))
    ctk.CTkButton(
        btn_row,
        text="Add link",
        command=add_link_cb,
        width=80,
        **ghost,
    ).pack(side="left", padx=(4, 0))
    ctk.CTkButton(
        btn_row,
        text="Close",
        command=close_cb,
        width=56,
        height=26,
        corner_radius=6,
        fg_color="#8b3a3a",
        hover_color="#a44444",
        font=ctk.CTkFont(size=12),
    ).pack(side="left", padx=(8, 0))

    drag = ctk.CTkFrame(strip, fg_color=COLOR_STRIP, corner_radius=0)
    drag.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=4)
    ctk.CTkLabel(
        drag,
        text="StreamPanel — drag here to move",
        font=ctk.CTkFont(size=12),
        text_color=("gray70", "gray65"),
        anchor="w",
    ).pack(side="left")
    _bind_drag_region(drag, root)

    body = ctk.CTkFrame(root, fg_color=COLOR_BG, corner_radius=0)
    body.pack(fill="both", expand=True)
    return body
