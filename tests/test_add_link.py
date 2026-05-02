"""Tests for streampanel.add_link_dialog helpers and .url + store sync."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from streampanel import store
from streampanel.add_link_dialog import (
    default_stem_from_url,
    pick_unique_url_filename,
    sanitize_filename_stem,
)
from streampanel.url_shortcut import internet_shortcut_body, normalize_url


class AddLinkHelpersTests(unittest.TestCase):
    def test_sanitize_filename_stem(self) -> None:
        self.assertEqual(sanitize_filename_stem('a<b>c|d'), "a-b-c-d")
        self.assertEqual(sanitize_filename_stem("  x  "), "x")

    def test_default_stem_from_url(self) -> None:
        s = default_stem_from_url("https://example.com/foo/bar")
        self.assertIn("example.com", s)
        self.assertIn("foo", s)

    def test_pick_unique_url_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.assertEqual(pick_unique_url_filename(d, "foo"), d / "foo.url")
            (d / "foo.url").write_text("x", encoding="ascii")
            self.assertEqual(pick_unique_url_filename(d, "foo"), d / "foo-2.url")


class AddLinkStoreIntegrationTests(unittest.TestCase):
    def test_write_url_sync_picks_up_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shortcuts = root / "sc"
            shortcuts.mkdir()
            db = root / "t.db"
            url = normalize_url("https://sync.test/page")
            path = pick_unique_url_filename(shortcuts, "SyncTest")
            path.write_text(internet_shortcut_body(url), encoding="utf-8")

            conn = store.connect(db)
            try:
                r = store.sync_from_folder(conn, shortcuts)
                self.assertEqual(len(r.added_paths), 1)
                items = store.list_items(conn)
                self.assertEqual(len(items), 1)
                resolved = items[0].source_path.lower()
                self.assertTrue(resolved.endswith("synctest.url"), msg=resolved)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
