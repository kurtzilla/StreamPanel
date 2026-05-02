"""Tests for streampanel.panel_dnd helpers."""

from __future__ import annotations

import unittest
from pathlib import Path

from streampanel.panel_dnd import paths_from_dnd_files


class PanelDndTests(unittest.TestCase):
    def test_paths_braced(self) -> None:
        s = r"{C:\Program Files\a.url} {D:\b.url}"
        paths = paths_from_dnd_files(s)
        self.assertEqual(paths, [Path(r"C:\Program Files\a.url"), Path(r"D:\b.url")])

    def test_paths_unquoted(self) -> None:
        paths = paths_from_dnd_files(r"C:\x\my.url")
        self.assertEqual(paths, [Path(r"C:\x\my.url")])

    def test_paths_empty(self) -> None:
        self.assertEqual(paths_from_dnd_files(""), [])
        self.assertEqual(paths_from_dnd_files("   "), [])


if __name__ == "__main__":
    unittest.main()
