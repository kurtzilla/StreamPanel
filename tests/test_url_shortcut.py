"""Tests for streampanel.url_shortcut."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from streampanel.url_shortcut import (
    internet_shortcut_body,
    looks_like_single_http_url,
    normalize_url,
    parse_internet_shortcut,
)


class UrlShortcutTests(unittest.TestCase):
    def test_normalize_url(self) -> None:
        self.assertEqual(
            normalize_url("  https://Example.COM/foo?x=1  "),
            "https://example.com/foo?x=1",
        )
        self.assertEqual(normalize_url("http://localhost"), "http://localhost")

    def test_normalize_url_errors(self) -> None:
        for bad in ("", "   ", "ftp://a.com", "https://", "not-a-url"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    normalize_url(bad)

    def test_internet_shortcut_body_minimal(self) -> None:
        u = "https://example.com/a"
        self.assertEqual(internet_shortcut_body(u), f"[InternetShortcut]\nURL={u}\n")

    def test_internet_shortcut_body_with_icon(self) -> None:
        u = "https://example.com/"
        body = internet_shortcut_body(u, icon_file=r"C:\icons\a.ico", icon_index=2)
        self.assertIn("[InternetShortcut]", body)
        self.assertIn(f"URL={u}", body)
        self.assertIn(r"IconFile=C:\icons\a.ico", body)
        self.assertIn("IconIndex=2", body)

    def test_parse_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.url"
            orig = internet_shortcut_body(
                "https://x.example/path",
                icon_file="D:\\z\\ico.dll",
                icon_index=5,
            )
            p.write_text(orig, encoding="utf-8")
            parsed = parse_internet_shortcut(p)
            self.assertEqual(parsed.url, "https://x.example/path")
            self.assertEqual(parsed.icon_file, "D:\\z\\ico.dll")
            self.assertEqual(parsed.icon_index, 5)

    def test_parse_case_insensitive_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.url"
            p.write_text(
                "[internetshortcut]\nurl=https://lowercase.keys/\n"
                "iconfile=C:\\a.ico\niconindex=1\n",
                encoding="utf-8",
            )
            parsed = parse_internet_shortcut(p)
            self.assertEqual(parsed.url, "https://lowercase.keys/")
            self.assertEqual(parsed.icon_file, r"C:\a.ico")
            self.assertEqual(parsed.icon_index, 1)

    def test_looks_like_single_http_url(self) -> None:
        self.assertTrue(looks_like_single_http_url("https://a.com/x"))
        self.assertFalse(looks_like_single_http_url("hello https://a.com"))
        self.assertFalse(looks_like_single_http_url(""))


if __name__ == "__main__":
    unittest.main()
