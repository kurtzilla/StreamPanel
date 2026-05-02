"""Minimal CTk shell; deck UI comes in later slices."""

from __future__ import annotations

import customtkinter as ctk

from streampanel import store
from streampanel.panel_layout import (
    MIN_PANEL_WIDTH,
    clamp_root_geometry,
    max_panel_height,
    min_panel_height,
)
from streampanel.shortcuts_folder import default_shortcuts_dir
from streampanel.win_overlay import apply_tool_window_overlay
from streampanel.window_chrome import _stub_dialog, apply_borderless_chrome


def run() -> None:
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.title("StreamPanel")

    conn = store.connect()
    try:
        shortcuts = default_shortcuts_dir()
        sync = store.sync_from_folder(conn, shortcuts)
        n = len(store.list_items(conn))
        shell = store.load_panel_shell_state(conn)
        subtitle = (
            f"{n} shortcut(s) in DB — sync +{len(sync.added_paths)} / −{len(sync.removed_ids)}.\n"
            f"Shortcuts folder:\n{shortcuts}"
        )
    finally:
        conn.close()

    shell_state: dict[str, bool] = {"top": shell.always_on_top}
    min_h = min_panel_height(n)

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

    def flush_layout_and_persist() -> None:
        debounce_id[0] = None
        min_h2 = min_panel_height(n)
        max_h2 = max_panel_height(n)
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
        persist_now()

    def schedule_persist(_event: object | None = None) -> None:
        if debounce_id[0] is not None:
            root.after_cancel(debounce_id[0])
        debounce_id[0] = root.after(250, flush_layout_and_persist)

    def on_pin_toggled(v: bool) -> None:
        shell_state["top"] = v
        persist_now()

    def on_add_link() -> None:
        _stub_dialog(root, "Add link", "Add-link dialog comes in add-link-ux.")

    def on_close() -> None:
        persist_now()
        root.destroy()

    body = apply_borderless_chrome(
        root,
        always_on_top=shell_state["top"],
        on_pin_toggled=on_pin_toggled,
        on_add_link=on_add_link,
        on_close=on_close,
    )

    def on_configure(event: object) -> None:
        ev = event  # type: ignore[assignment]
        if ev.widget is not root:
            return
        schedule_persist()

    root.bind("<Configure>", on_configure)

    inner = ctk.CTkFrame(body, fg_color="transparent")
    inner.pack(expand=True, fill="both", padx=20, pady=16)

    ctk.CTkLabel(
        inner,
        text="Status",
        font=ctk.CTkFont(size=16, weight="bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 6))
    ctk.CTkLabel(
        inner,
        text=subtitle,
        wraplength=430,
        justify="left",
        anchor="w",
    ).pack(fill="x", pady=(0, 8))

    ghost = dict(
        corner_radius=8,
        fg_color="#2a2a2a",
        hover_color="#3d3d3d",
        font=ctk.CTkFont(size=13),
        height=48,
    )
    row = ctk.CTkFrame(inner, fg_color="transparent", height=56)
    row.pack(fill="x", pady=(4, 0))
    row.pack_propagate(False)
    ctk.CTkButton(
        row,
        text="+  Add shortcut (ghost row)",
        command=on_add_link,
        anchor="w",
        **ghost,
    ).pack(fill="x", expand=True)

    root.after_idle(lambda: root.after(0, flush_layout_and_persist))
    root.after(100, lambda: apply_tool_window_overlay(root))

    root.mainloop()
