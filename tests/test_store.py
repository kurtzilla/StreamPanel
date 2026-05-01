"""Tests for streampanel.store."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from streampanel import store


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "t.db"
        self.shortcuts = self.root / "shortcuts"
        self.shortcuts.mkdir()

    def test_sync_insert_remove(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)

        a = self.shortcuts / "a.url"
        b = self.shortcuts / "b.lnk"
        a.write_text("[InternetShortcut]\nURL=https://example.com/\n", encoding="ascii")
        b.write_bytes(b"\0")

        r1 = store.sync_from_folder(conn, self.shortcuts)
        self.assertEqual(len(r1.added_paths), 2)
        self.assertEqual(r1.removed_ids, ())

        items = store.list_items(conn)
        self.assertEqual(len(items), 2)
        paths = {i.source_path for i in items}
        self.assertEqual(paths, {str(a.resolve()), str(b.resolve())})

        a.unlink()
        r2 = store.sync_from_folder(conn, self.shortcuts)
        self.assertEqual(len(r2.added_paths), 0)
        self.assertEqual(len(r2.removed_ids), 1)
        self.assertEqual(len(store.list_items(conn)), 1)

    def test_reorder_update_flags_viewer_rect(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)

        for name in ("x.url", "y.url"):
            p = self.shortcuts / name
            p.write_text("[InternetShortcut]\nURL=https://t/\n", encoding="ascii")

        store.sync_from_folder(conn, self.shortcuts)
        items = store.list_items(conn)
        self.assertEqual(len(items), 2)
        first_id, second_id = items[0].id, items[1].id

        store.reorder_items(conn, [second_id, first_id])
        items = store.list_items(conn)
        self.assertEqual([i.id for i in items], [second_id, first_id])
        self.assertEqual(items[0].sort_order, 0)
        self.assertEqual(items[1].sort_order, 1)

        ok = store.update_item(
            conn,
            second_id,
            label_override="Hello",
            flags={"confirm_launch": True},
            viewer_rect=(1, 2, 800, 600),
        )
        self.assertTrue(ok)
        row = store.get_item(conn, second_id)
        assert row is not None
        self.assertEqual(row.label_override, "Hello")
        self.assertEqual(store.parse_flags(row), {"confirm_launch": True})
        self.assertEqual(row.viewer_rect_x, 1)

        store.update_item(conn, second_id, clear_viewer_rect=True)
        row2 = store.get_item(conn, second_id)
        assert row2 is not None
        self.assertIsNone(row2.viewer_rect_x)

        self.assertTrue(store.delete_item(conn, first_id))
        self.assertIsNone(store.get_item(conn, first_id))


if __name__ == "__main__":
    unittest.main()
