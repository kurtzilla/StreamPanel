"""Tests for streampanel.store."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from streampanel import store
from streampanel.panel_layout import DEFAULT_GRID_COLS
from streampanel.shortcuts_folder import default_shortcuts_dir, resolve_shortcuts_dir


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

    def test_app_kv_migration_and_panel_shell(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)

        self.assertIsNone(store.app_kv_get(conn, "k"))
        store.app_kv_set(conn, "k", "v")
        self.assertEqual(store.app_kv_get(conn, "k"), "v")
        store.app_kv_set(conn, "k", "v2")
        self.assertEqual(store.app_kv_get(conn, "k"), "v2")

        s0 = store.load_panel_shell_state(conn)
        self.assertFalse(s0.always_on_top)
        self.assertIsNone(s0.x)

        store.save_panel_shell_state(
            conn,
            always_on_top=True,
            x=10,
            y=20,
            w=400,
            h=300,
            screen_number=1,
        )
        s1 = store.load_panel_shell_state(conn)
        self.assertTrue(s1.always_on_top)
        self.assertEqual(s1.x, 10)
        self.assertEqual(s1.y, 20)
        self.assertEqual(s1.w, 400)
        self.assertEqual(s1.h, 300)
        self.assertEqual(s1.screen_number, 1)

    def test_app_settings_defaults_when_missing(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        s = store.load_app_settings(conn)
        self.assertEqual(s.appearance_mode, "dark")
        self.assertIsNone(s.shortcuts_dir)
        self.assertEqual(s.grid_cols, DEFAULT_GRID_COLS)

    def test_app_settings_round_trip(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        custom = self.shortcuts / "custom"
        custom.mkdir()
        s_in = store.AppSettings(
            appearance_mode="light",
            shortcuts_dir=custom,
            grid_cols=3,
        )
        store.save_app_settings(conn, s_in)
        s_out = store.load_app_settings(conn)
        self.assertEqual(s_out.appearance_mode, "light")
        self.assertEqual(s_out.shortcuts_dir, custom)
        self.assertEqual(s_out.grid_cols, 3)

    def test_app_settings_corrupt_json_uses_defaults(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        store.app_kv_set(conn, "app_settings_v1", "{not json")
        s = store.load_app_settings(conn)
        self.assertEqual(s.appearance_mode, "dark")
        self.assertIsNone(s.shortcuts_dir)

    def test_app_settings_invalid_values_clamped_or_defaulted(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        store.app_kv_set(
            conn,
            "app_settings_v1",
            '{"appearance_mode":"neon","grid_cols":99,"shortcuts_dir":42}',
        )
        s = store.load_app_settings(conn)
        self.assertEqual(s.appearance_mode, "dark")
        self.assertIsNone(s.shortcuts_dir)
        self.assertEqual(s.grid_cols, 8)

        store.app_kv_set(
            conn,
            "app_settings_v1",
            '{"appearance_mode":"system","grid_cols":1}',
        )
        s2 = store.load_app_settings(conn)
        self.assertEqual(s2.appearance_mode, "system")
        self.assertEqual(s2.grid_cols, 2)

    def test_resolve_shortcuts_dir_override_and_fallback(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        custom = self.shortcuts / "alt"
        custom.mkdir()
        self.assertEqual(resolve_shortcuts_dir(custom), custom.resolve())
        self.assertEqual(
            resolve_shortcuts_dir(self.shortcuts / "nope"),
            default_shortcuts_dir(),
        )

    def test_clear_label_override_and_notes(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)

        p = self.shortcuts / "z.url"
        p.write_text("[InternetShortcut]\nURL=https://z/\n", encoding="ascii")
        store.sync_from_folder(conn, self.shortcuts)
        items = store.list_items(conn)
        self.assertEqual(len(items), 1)
        zid = items[0].id

        store.update_item(conn, zid, label_override="Custom", notes="hello")
        row = store.get_item(conn, zid)
        assert row is not None
        self.assertEqual(row.label_override, "Custom")
        self.assertEqual(row.notes, "hello")

        store.update_item(conn, zid, clear_label_override=True, label_override=None)
        row2 = store.get_item(conn, zid)
        assert row2 is not None
        self.assertIsNone(row2.label_override)
        self.assertEqual(row2.notes, "hello")

        store.update_item(conn, zid, clear_notes=True, notes=None)
        row3 = store.get_item(conn, zid)
        assert row3 is not None
        self.assertIsNone(row3.notes)


if __name__ == "__main__":
    unittest.main()
