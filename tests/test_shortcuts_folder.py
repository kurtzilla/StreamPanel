"""Tests for streampanel.shortcuts_folder (portable data dir)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streampanel.shortcuts_folder import (
    DATA_DIR_ENV,
    PortableDataDirError,
    default_db_path,
    default_shortcuts_dir,
    user_data_dir,
)


class PortableDataDirTests(unittest.TestCase):
    def test_streampanel_data_dir_redirects_user_data(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            portable = Path(d) / "portable_root"
            env = {DATA_DIR_ENV: str(portable)}
            with patch.dict(os.environ, env, clear=False):
                u = user_data_dir()
                self.assertEqual(u.resolve(), portable.resolve())
                self.assertTrue(portable.is_dir())
                self.assertEqual(
                    default_db_path().resolve(), (portable / "streampanel.db").resolve()
                )
                self.assertEqual(
                    default_shortcuts_dir().resolve(),
                    (portable / "shortcuts").resolve(),
                )

    def test_empty_env_uses_standard_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_appdata = Path(tmp) / "appdata"
            fake_appdata.mkdir()
            env = {DATA_DIR_ENV: "   ", "APPDATA": str(fake_appdata)}
            with patch.dict(os.environ, env, clear=False):
                u = user_data_dir()
                self.assertEqual(u.parent.resolve(), fake_appdata.resolve())
                self.assertEqual(u.name, "StreamPanel")

    def test_file_path_raises(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            fp = f.name
        try:
            env = {DATA_DIR_ENV: fp}
            with patch.dict(os.environ, env, clear=False):
                with self.assertRaises(PortableDataDirError):
                    user_data_dir()
        finally:
            os.unlink(fp)


if __name__ == "__main__":
    unittest.main()
