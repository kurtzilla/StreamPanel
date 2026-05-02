"""Tests for streampanel.runtime_shell."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from streampanel.runtime_shell import ShellOpenError, open_path


class TestRuntimeShell(unittest.TestCase):
    def test_missing_file_raises_shell_open_error(self) -> None:
        with TemporaryDirectory() as td:
            missing = Path(td) / "nope.url"
            with self.assertRaises(ShellOpenError) as ctx:
                open_path(missing)
            self.assertIn("missing", str(ctx.exception).lower())

    def test_directory_raises_shell_open_error(self) -> None:
        with TemporaryDirectory() as td:
            with self.assertRaises(ShellOpenError):
                open_path(Path(td))

    @unittest.skipUnless(sys.platform == "win32", "os.startfile is Windows-only")
    def test_windows_calls_startfile(self) -> None:
        with TemporaryDirectory() as td:
            f = Path(td) / "x.url"
            f.write_text("[InternetShortcut]\nURL=https://example.com/\n", encoding="ascii")
            with patch("streampanel.runtime_shell.os.startfile") as mock_sf:
                open_path(f)
            mock_sf.assert_called_once()
            args, _kwargs = mock_sf.call_args
            self.assertEqual(args[1], "open")
            self.assertTrue(str(args[0]).endswith("x.url"))

    @unittest.skipIf(sys.platform == "win32", "non-Windows branch")
    def test_non_windows_raises_not_implemented(self) -> None:
        with TemporaryDirectory() as td:
            f = Path(td) / "x.url"
            f.write_text("x", encoding="ascii")
            with self.assertRaises(NotImplementedError):
                open_path(f)


if __name__ == "__main__":
    unittest.main()
