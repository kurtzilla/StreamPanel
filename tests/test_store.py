"""Tests for streampanel.store."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from streampanel import store, themes
from streampanel.panel_layout import DEFAULT_GRID_COLS
from streampanel.shortcuts_folder import default_shortcuts_dir, resolve_shortcuts_dir
from streampanel.url_shortcut import normalize_url


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

    def test_merge_full_order_after_visible_reorder(self) -> None:
        full = [10, 20, 30, 40]
        vis = frozenset({10, 30, 40})
        new_vis = [40, 10, 30]
        merged = store.merge_full_order_after_visible_reorder(
            full, new_vis, visible_id_set=vis
        )
        self.assertEqual(merged, [40, 20, 10, 30])

        merged2 = store.merge_full_order_after_visible_reorder(
            [1, 2, 3], [3, 1, 2], visible_id_set=frozenset({1, 2, 3})
        )
        self.assertEqual(merged2, [3, 1, 2])

        with self.assertRaises(ValueError):
            store.merge_full_order_after_visible_reorder(
                full, [40, 10], visible_id_set=vis
            )
        with self.assertRaises(ValueError):
            store.merge_full_order_after_visible_reorder(
                full, [40, 10, 99], visible_id_set=vis
            )

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

    def test_public_settings_constants(self) -> None:
        self.assertEqual(set(store.APPEARANCE_MODES), {"dark", "light", "system"})
        self.assertEqual(store.GRID_COLS_MIN, 2)
        self.assertEqual(store.GRID_COLS_MAX, 8)
        self.assertEqual(store.clamp_grid_cols(1), 2)
        self.assertEqual(store.clamp_grid_cols(99), 8)
        self.assertEqual(store.clamp_grid_cols(4), 4)
        self.assertEqual(store.clamp_ui_scale(1.0), 1.0)
        self.assertEqual(store.clamp_ui_scale(0.5), store.UI_SCALE_MIN)
        self.assertEqual(store.clamp_ui_scale(9.0), store.UI_SCALE_MAX)

    def test_app_settings_defaults_when_missing(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        s = store.load_app_settings(conn)
        self.assertEqual(s.appearance_mode, "dark")
        self.assertEqual(s.ui_theme, themes.default_theme_id())
        self.assertIsNone(s.shortcuts_dir)
        self.assertEqual(s.grid_cols, DEFAULT_GRID_COLS)
        self.assertEqual(s.deck_cell_px, store.DEFAULT_DECK_CELL_PX)
        self.assertFalse(s.deck_show_hidden_items)
        self.assertEqual(s.ui_scale, store.UI_SCALE_DEFAULT)
        self.assertEqual(s.deck_primary_action, store.DECK_PRIMARY_CHANNELS)
        self.assertEqual(
            s.window_startup_placement, store.WINDOW_STARTUP_CENTER
        )

    def test_app_settings_round_trip(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        custom = self.shortcuts / "custom"
        custom.mkdir()
        s_in = store.AppSettings(
            appearance_mode="light",
            ui_theme="ocean",
            shortcuts_dir=custom,
            grid_cols=3,
            deck_cell_px=56,
            deck_show_hidden_items=True,
            ui_scale=1.25,
            deck_primary_action=store.DECK_PRIMARY_LAUNCH,
            window_startup_placement=store.WINDOW_STARTUP_LAST_POSITION,
        )
        store.save_app_settings(conn, s_in)
        s_out = store.load_app_settings(conn)
        self.assertEqual(s_out.appearance_mode, "light")
        self.assertEqual(s_out.ui_theme, "ocean")
        self.assertEqual(s_out.shortcuts_dir, custom)
        self.assertEqual(s_out.grid_cols, 3)
        self.assertEqual(s_out.deck_cell_px, 56)
        self.assertTrue(s_out.deck_show_hidden_items)
        self.assertEqual(s_out.ui_scale, 1.25)
        self.assertEqual(s_out.deck_primary_action, store.DECK_PRIMARY_LAUNCH)
        self.assertEqual(
            s_out.window_startup_placement, store.WINDOW_STARTUP_LAST_POSITION
        )

    def test_app_settings_corrupt_json_uses_defaults(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        store.app_kv_set(conn, "app_settings_v1", "{not json")
        s = store.load_app_settings(conn)
        self.assertEqual(s.appearance_mode, "dark")
        self.assertIsNone(s.shortcuts_dir)
        self.assertEqual(s.ui_scale, store.UI_SCALE_DEFAULT)

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
        self.assertEqual(s.ui_scale, store.UI_SCALE_DEFAULT)

        store.app_kv_set(
            conn,
            "app_settings_v1",
            '{"appearance_mode":"system","grid_cols":1}',
        )
        s2 = store.load_app_settings(conn)
        self.assertEqual(s2.appearance_mode, "system")
        self.assertEqual(s2.grid_cols, 2)
        self.assertFalse(s2.deck_show_hidden_items)

        store.app_kv_set(
            conn,
            "app_settings_v1",
            '{"appearance_mode":"dark","ui_scale":99}',
        )
        s3 = store.load_app_settings(conn)
        self.assertEqual(s3.ui_scale, store.UI_SCALE_MAX)

        store.app_kv_set(
            conn,
            "app_settings_v1",
            '{"appearance_mode":"dark","ui_scale":0.01}',
        )
        s4 = store.load_app_settings(conn)
        self.assertEqual(s4.ui_scale, store.UI_SCALE_MIN)

        store.app_kv_set(
            conn,
            "app_settings_v1",
            '{"appearance_mode":"dark","ui_scale":"nope"}',
        )
        s5 = store.load_app_settings(conn)
        self.assertEqual(s5.ui_scale, store.UI_SCALE_DEFAULT)

        store.app_kv_set(
            conn,
            "app_settings_v1",
            '{"appearance_mode":"dark","deck_primary_action":"bogus"}',
        )
        s6 = store.load_app_settings(conn)
        self.assertEqual(s6.deck_primary_action, store.DECK_PRIMARY_CHANNELS)

        store.app_kv_set(
            conn,
            "app_settings_v1",
            '{"appearance_mode":"dark","deck_cell_px":200}',
        )
        s_cell = store.load_app_settings(conn)
        self.assertEqual(s_cell.deck_cell_px, store.DECK_CELL_PX_MAX)

        store.app_kv_set(
            conn,
            "app_settings_v1",
            '{"appearance_mode":"dark","ui_theme":"not_a_real_theme"}',
        )
        s7 = store.load_app_settings(conn)
        self.assertEqual(s7.ui_theme, themes.default_theme_id())

        store.app_kv_set(
            conn,
            "app_settings_v1",
            '{"appearance_mode":"dark","window_startup_placement":"nope"}',
        )
        s8 = store.load_app_settings(conn)
        self.assertEqual(s8.window_startup_placement, store.WINDOW_STARTUP_CENTER)

    def test_export_db_to_file(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        p = self.shortcuts / "a.url"
        p.write_text("[InternetShortcut]\nURL=https://a/\n", encoding="ascii")
        store.sync_from_folder(conn, self.shortcuts)
        self.assertEqual(len(store.list_items(conn)), 1)
        v = int(conn.execute("PRAGMA user_version").fetchone()[0])
        conn.close()

        backup = self.root / "backup.db"
        store.export_db_to_file(backup, source=self.db)
        self.assertTrue(backup.is_file())

        conn2 = sqlite3.connect(str(backup))
        self.addCleanup(conn2.close)
        self.assertEqual(
            int(conn2.execute("PRAGMA user_version").fetchone()[0]),
            v,
        )
        n = int(conn2.execute("SELECT COUNT(*) FROM deck_items").fetchone()[0])
        self.assertEqual(n, 1)

        with self.assertRaises(ValueError):
            store.export_db_to_file(self.db, source=self.db)

    def test_launch_events_migration_and_record(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        v = int(conn.execute("PRAGMA user_version").fetchone()[0])
        self.assertGreaterEqual(v, 3)
        store.record_item_open(conn, item_id=42, source_path=r"C:\x\a.url")
        cur = conn.cursor()
        n = cur.execute("SELECT COUNT(*) FROM launch_events").fetchone()[0]
        self.assertEqual(int(n), 1)
        row = cur.execute(
            "SELECT item_id, source_path, kind FROM launch_events LIMIT 1"
        ).fetchone()
        assert row is not None
        self.assertEqual(row["item_id"], 42)
        self.assertEqual(row["source_path"], r"C:\x\a.url")
        self.assertEqual(row["kind"], "view")

    def test_list_launch_events_for_item_order_and_limit(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        store.record_item_open(conn, item_id=7, source_path=r"C:\a.url", kind="view")
        store.record_item_open(conn, item_id=7, source_path=r"C:\a.url", kind="launch")
        store.record_item_open(conn, item_id=7, source_path=r"C:\a.url", kind="view")
        store.record_item_open(conn, item_id=8, source_path=r"C:\b.url", kind="view")
        ev = store.list_launch_events_for_item(conn, 7, limit=2)
        self.assertEqual(len(ev), 2)
        self.assertEqual(ev[0].kind, "view")
        self.assertEqual(ev[1].kind, "launch")
        ev_all = store.list_launch_events_for_item(conn, 7, limit=20)
        self.assertEqual(len(ev_all), 3)
        self.assertEqual(store.list_launch_events_for_item(conn, 99, limit=5), [])

    def test_list_deck_items_respects_hide_flag(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        a = self.shortcuts / "a.url"
        b = self.shortcuts / "b.url"
        a.write_text("[InternetShortcut]\nURL=https://a/\n", encoding="ascii")
        b.write_text("[InternetShortcut]\nURL=https://b/\n", encoding="ascii")
        store.sync_from_folder(conn, self.shortcuts)
        items = store.list_items(conn)
        self.assertEqual(len(items), 2)
        hid = next(i for i in items if "a.url" in i.source_path)
        store.update_item(conn, hid.id, flags={store.FLAG_HIDE_FROM_DECK: True})
        st_hide = store.default_app_settings()
        visible = store.list_deck_items(conn, st_hide)
        self.assertEqual(len(visible), 1)
        self.assertIn("b.url", visible[0].source_path)
        st_show = store.AppSettings(
            appearance_mode=st_hide.appearance_mode,
            ui_theme=st_hide.ui_theme,
            shortcuts_dir=st_hide.shortcuts_dir,
            grid_cols=st_hide.grid_cols,
            deck_cell_px=st_hide.deck_cell_px,
            deck_show_hidden_items=True,
            ui_scale=st_hide.ui_scale,
            deck_primary_action=st_hide.deck_primary_action,
            window_startup_placement=st_hide.window_startup_placement,
        )
        all_vis = store.list_deck_items(conn, st_show)
        self.assertEqual(len(all_vis), 2)

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

        store.update_item(conn, zid, icon_path="C:\\icons\\x.ico")
        row4 = store.get_item(conn, zid)
        assert row4 is not None
        self.assertEqual(row4.icon_path, "C:\\icons\\x.ico")
        self.assertEqual(store.get_item_id_for_source_path(conn, p), zid)
        store.update_item(conn, zid, clear_icon_path=True)
        row5 = store.get_item(conn, zid)
        assert row5 is not None
        self.assertIsNone(row5.icon_path)

    def test_get_item_id_for_source_path_missing(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        self.assertIsNone(
            store.get_item_id_for_source_path(conn, self.shortcuts / "nope.url")
        )

    def test_deck_has_normalized_url(self) -> None:
        conn = store.connect(self.db)
        self.addCleanup(conn.close)
        a = self.shortcuts / "a.url"
        b = self.shortcuts / "b.url"
        a.write_text("[InternetShortcut]\nURL=https://dup.test/\n", encoding="ascii")
        b.write_text("[InternetShortcut]\nURL=https://other.test/\n", encoding="ascii")
        store.sync_from_folder(conn, self.shortcuts)
        self.assertTrue(store.deck_has_normalized_url(conn, "https://dup.test/"))
        self.assertTrue(store.deck_has_normalized_url(conn, normalize_url("HTTPS://DUP.test/")))
        self.assertFalse(store.deck_has_normalized_url(conn, "https://missing.example/"))
        self.assertFalse(store.deck_has_normalized_url(conn, normalize_url("https://dup.test/extra")))


if __name__ == "__main__":
    unittest.main()
