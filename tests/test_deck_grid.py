"""Tests for streampanel.deck_grid (no GUI)."""

from __future__ import annotations

import unittest
from pathlib import Path

from streampanel.deck_grid import item_display_label
from streampanel.store import DeckItem


def _item(
    *,
    source_path: str,
    label_override: str | None = None,
    item_id: int = 1,
) -> DeckItem:
    return DeckItem(
        id=item_id,
        source_path=source_path,
        sort_order=0,
        grid_row=None,
        grid_col=None,
        label_override=label_override,
        icon_path=None,
        notes=None,
        flags_json=None,
        viewer_rect_x=None,
        viewer_rect_y=None,
        viewer_rect_w=None,
        viewer_rect_h=None,
    )


class DeckGridLabelTests(unittest.TestCase):
    def test_label_stem(self) -> None:
        it = _item(source_path=str(Path("C:/d/e/My Channel.url")))
        self.assertEqual(item_display_label(it), "My Channel")

    def test_label_override(self) -> None:
        it = _item(source_path="x.url", label_override="  Live  ")
        self.assertEqual(item_display_label(it), "Live")

    def test_label_truncation(self) -> None:
        long_stem = "A" * 40
        it = _item(source_path=f"{long_stem}.url")
        out = item_display_label(it, max_len=10)
        self.assertEqual(len(out), 10)
        self.assertTrue(out.endswith("…"))


if __name__ == "__main__":
    unittest.main()
