"""Deck grid: sort_order-major cells, optional extra ghost row when the shell is near max height."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk

_DRAG_THRESHOLD_PX = 8
_CELL_ICON_PX = 24

from streampanel.panel_layout import (
    DEFAULT_GRID_COLS,
    ROW_H,
    content_rows,
    max_panel_height,
)
from streampanel.store import DeckItem, clamp_grid_cols


def item_display_label(item: DeckItem, *, max_len: int = 22) -> str:
    if item.label_override and item.label_override.strip():
        s = item.label_override.strip()
    else:
        s = Path(item.source_path).stem
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def item_matches_search(item: DeckItem, query: str) -> bool:
    """Case-insensitive match on display label, filename stem, or full source path."""
    q = query.strip().lower()
    if not q:
        return True
    label = item_display_label(item, max_len=999).lower()
    stem = Path(item.source_path).stem.lower()
    path_l = item.source_path.lower()
    return q in label or q in stem or q in path_l


def _ghost_style() -> dict[str, object]:
    return dict(
        corner_radius=8,
        fg_color="#2a2a2a",
        hover_color="#3d3d3d",
        font=ctk.CTkFont(size=12),
        height=ROW_H - 8,
    )


def _cell_style() -> dict[str, object]:
    return dict(
        corner_radius=8,
        fg_color="#323232",
        hover_color="#404040",
        font=ctk.CTkFont(size=12),
        height=ROW_H - 8,
        anchor="center",
    )


def _try_cell_icon(item: DeckItem) -> ctk.CTkImage | None:
    if not item.icon_path:
        return None
    p = Path(item.icon_path)
    if not p.is_file():
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        pil = Image.open(p)
        pil = pil.convert("RGBA")
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS  # type: ignore[attr-defined]
        pil = pil.resize((_CELL_ICON_PX, _CELL_ICON_PX), resample)
        return ctk.CTkImage(
            light_image=pil,
            dark_image=pil,
            size=(_CELL_ICON_PX, _CELL_ICON_PX),
        )
    except OSError:
        return None


class DeckGridView:
    """Renders deck items in a fixed column count; optional bottom ghost row for add."""

    def __init__(
        self,
        parent: ctk.CTkFrame,
        *,
        cols: int = DEFAULT_GRID_COLS,
        on_item_primary: Callable[[DeckItem], None],
        on_item_edit: Callable[[DeckItem], None],
        on_add: Callable[[], None],
        on_reorder: Callable[[int, int], None] | None = None,
        primary_click_delay_ms: int = 0,
        on_item_double_click: Callable[[DeckItem], None] | None = None,
    ) -> None:
        self._on_primary = on_item_primary
        self._on_edit = on_item_edit
        self._on_add = on_add
        self._on_reorder = on_reorder
        self._primary_delay_ms = max(0, int(primary_click_delay_ms))
        self._on_double = on_item_double_click
        self._items: list[DeckItem] = []
        self._cols = clamp_grid_cols(cols)
        self._deck = ctk.CTkFrame(parent, fg_color="transparent")
        self._rows_host = ctk.CTkFrame(self._deck, fg_color="transparent")
        self._rows_host.pack(fill="x", expand=True)
        self._extra_row = ctk.CTkFrame(self._deck, fg_color="transparent", height=ROW_H)
        self._extra_row.pack_propagate(False)
        self._pack_extra = False
        self._press: tuple[int, int, int, DeckItem] | None = None
        self._dragging = False
        self._defer_after_id: int | None = None
        self._suppress_next_primary = False
        self._cell_image_refs: list[ctk.CTkImage] = []

    @property
    def widget(self) -> ctk.CTkFrame:
        return self._deck

    def set_cols(self, n: int) -> None:
        self._cols = clamp_grid_cols(n)
        self.rebuild(self._items)

    def set_primary_interaction(
        self,
        *,
        primary_click_delay_ms: int,
        on_item_double_click: Callable[[DeckItem], None] | None,
    ) -> None:
        self._cancel_deferred_primary()
        self._primary_delay_ms = max(0, int(primary_click_delay_ms))
        self._on_double = on_item_double_click

    def set_reorder_handler(self, cb: Callable[[int, int], None] | None) -> None:
        self._on_reorder = cb

    def _cancel_deferred_primary(self) -> None:
        if self._defer_after_id is not None:
            try:
                self._deck.winfo_toplevel().after_cancel(self._defer_after_id)
            except Exception:
                pass
            self._defer_after_id = None

    def _schedule_primary(self, item: DeckItem) -> None:
        self._cancel_deferred_primary()
        top = self._deck.winfo_toplevel()

        def fire() -> None:
            self._defer_after_id = None
            self._on_primary(item)

        self._defer_after_id = int(top.after(self._primary_delay_ms, fire))

    def _index_under_xy(self, x_root: int, y_root: int) -> int | None:
        top = self._deck.winfo_toplevel()
        w = top.winfo_containing(x_root, y_root)
        while w is not None:
            idx = getattr(w, "_streampanel_deck_idx", None)
            if isinstance(idx, int):
                return idx
            w = getattr(w, "master", None)
        return None

    def _on_item_press(self, event: object, idx: int, item: DeckItem) -> None:
        ev = event  # type: ignore[assignment]
        self._press = (idx, int(ev.x_root), int(ev.y_root), item)
        self._dragging = False
        if self._on_reorder is not None:
            ev.widget.bind("<B1-Motion>", self._on_item_motion)

    def _on_item_motion(self, event: object) -> None:
        if self._press is None:
            return
        if self._on_reorder is None:
            return
        ev = event  # type: ignore[assignment]
        idx0, xr0, yr0, _ = self._press
        dx = int(ev.x_root) - xr0
        dy = int(ev.y_root) - yr0
        if dx * dx + dy * dy < _DRAG_THRESHOLD_PX * _DRAG_THRESHOLD_PX:
            return
        w = ev.widget
        w.unbind("<B1-Motion>")
        self._cancel_deferred_primary()
        self._dragging = True
        self._deck.grab_set()
        self._deck.bind("<B1-Motion>", self._on_drag_motion)
        self._deck.bind("<ButtonRelease-1>", self._on_drag_release)

    def _on_drag_motion(self, _event: object) -> None:
        pass

    def _on_drag_release(self, event: object) -> None:
        ev = event  # type: ignore[assignment]
        try:
            if self._press is None or self._on_reorder is None:
                return
            from_idx = self._press[0]
            to_idx = self._index_under_xy(int(ev.x_root), int(ev.y_root))
            if to_idx is not None and from_idx != to_idx:
                self._on_reorder(from_idx, to_idx)
        finally:
            self._deck.unbind("<B1-Motion>")
            self._deck.unbind("<ButtonRelease-1>")
            try:
                self._deck.grab_release()
            except Exception:
                pass
            self._press = None
            self._dragging = False

    def _handle_item_double(self, item: DeckItem) -> None:
        self._cancel_deferred_primary()
        self._suppress_next_primary = True
        if self._on_double is not None:
            self._on_double(item)

    def _on_item_release(self, event: object, _idx: int, item: DeckItem) -> None:
        ev = event  # type: ignore[assignment]
        try:
            ev.widget.unbind("<B1-Motion>")
        except Exception:
            pass
        if self._suppress_next_primary:
            self._suppress_next_primary = False
            self._press = None
            return
        if self._dragging:
            return
        if self._press is not None:
            if self._primary_delay_ms > 0:
                self._schedule_primary(item)
            else:
                self._on_primary(item)
        self._press = None

    def rebuild(self, items: list[DeckItem]) -> None:
        self._cancel_deferred_primary()
        self._cell_image_refs.clear()
        self._items = list(items)
        for w in self._rows_host.winfo_children():
            w.destroy()
        rows = content_rows(len(self._items), self._cols)
        ghost = _ghost_style()
        cell = _cell_style()
        for r in range(rows):
            row_f = ctk.CTkFrame(self._rows_host, fg_color="transparent", height=ROW_H)
            row_f.pack(fill="x", pady=(0, 4))
            row_f.pack_propagate(False)
            for c in range(self._cols):
                row_f.grid_columnconfigure(c, weight=1, uniform="deckcell")
                idx = r * self._cols + c
                if idx < len(self._items):
                    it = self._items[idx]
                    label = item_display_label(it)
                    icon = _try_cell_icon(it)
                    if icon is not None:
                        self._cell_image_refs.append(icon)
                    btn_kw: dict[str, object] = {**cell}
                    if icon is not None:
                        btn_kw["image"] = icon
                        btn_kw["compound"] = "left"
                    use_press_release = (
                        self._on_reorder is not None
                        or self._primary_delay_ms > 0
                        or self._on_double is not None
                    )
                    if use_press_release:
                        b = ctk.CTkButton(
                            row_f,
                            text=label,
                            **btn_kw,
                        )
                        setattr(b, "_streampanel_deck_idx", idx)
                        b.bind(
                            "<Button-1>",
                            lambda e, i=idx, t=it: self._on_item_press(e, i, t),
                        )
                        b.bind(
                            "<ButtonRelease-1>",
                            lambda e, i=idx, t=it: self._on_item_release(e, i, t),
                        )
                        if self._on_double is not None:
                            b.bind(
                                "<Double-Button-1>",
                                lambda _e, t=it: self._handle_item_double(t),
                            )
                    else:
                        b = ctk.CTkButton(
                            row_f,
                            text=label,
                            command=lambda i=it: self._on_primary(i),
                            **btn_kw,
                        )
                    b.grid(row=0, column=c, sticky="nsew", padx=4, pady=2)

                    def on_right(_e: object, i: DeckItem = it) -> str:
                        self._on_edit(i)
                        return "break"

                    b.bind("<Button-3>", on_right)
                elif idx < rows * self._cols:
                    ctk.CTkButton(
                        row_f,
                        text="+",
                        command=self._on_add,
                        **ghost,
                    ).grid(row=0, column=c, sticky="nsew", padx=4, pady=2)
        for w in self._extra_row.winfo_children():
            w.destroy()
        for c in range(self._cols):
            self._extra_row.grid_columnconfigure(c, weight=1, uniform="deckextra")
            ctk.CTkButton(
                self._extra_row,
                text="+ add",
                command=self._on_add,
                **_ghost_style(),
            ).grid(row=0, column=c, sticky="nsew", padx=4, pady=2)
        self._extra_row.pack_forget()
        self._pack_extra = False

    def sync_extra_row(self, root_height_px: int, item_count: int) -> None:
        hi = max_panel_height(item_count, self._cols)
        show = root_height_px >= hi - 20
        if show and not self._pack_extra:
            self._extra_row.pack(fill="x", pady=(4, 0))
            self._pack_extra = True
        elif not show and self._pack_extra:
            self._extra_row.pack_forget()
            self._pack_extra = False
