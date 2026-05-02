"""Deck grid: sort_order-major cells, optional extra ghost row when the shell is near max height."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk

from streampanel.panel_layout import (
    DEFAULT_GRID_COLS,
    ROW_H,
    content_rows,
    max_panel_height,
)
from streampanel.store import DeckItem


def item_display_label(item: DeckItem, *, max_len: int = 22) -> str:
    if item.label_override and item.label_override.strip():
        s = item.label_override.strip()
    else:
        s = Path(item.source_path).stem
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


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


class DeckGridView:
    """Renders deck items in a fixed column count; optional bottom ghost row for add."""

    def __init__(
        self,
        parent: ctk.CTkFrame,
        *,
        cols: int = DEFAULT_GRID_COLS,
        on_item_activated: Callable[[DeckItem], None],
        on_add: Callable[[], None],
    ) -> None:
        self._cols = cols
        self._on_item = on_item_activated
        self._on_add = on_add
        self._items: list[DeckItem] = []
        self._deck = ctk.CTkFrame(parent, fg_color="transparent")
        self._rows_host = ctk.CTkFrame(self._deck, fg_color="transparent")
        self._rows_host.pack(fill="x", expand=True)
        self._extra_row = ctk.CTkFrame(self._deck, fg_color="transparent", height=ROW_H)
        self._extra_row.pack_propagate(False)
        self._pack_extra = False

    @property
    def widget(self) -> ctk.CTkFrame:
        return self._deck

    def rebuild(self, items: list[DeckItem]) -> None:
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
                    b = ctk.CTkButton(
                        row_f,
                        text=item_display_label(it),
                        command=lambda i=it: self._on_item(i),
                        **cell,
                    )
                    b.grid(row=0, column=c, sticky="nsew", padx=4, pady=2)
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
