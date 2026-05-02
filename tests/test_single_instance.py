"""Tests for streampanel.single_instance (pure helpers)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from streampanel import single_instance


class SingleInstanceTests(unittest.TestCase):
    def test_mutex_name_stable(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "nested"
            p.mkdir()
            a = single_instance.mutex_name_for_data_dir(p)
            b = single_instance.mutex_name_for_data_dir(p.resolve())
            self.assertEqual(a, b)
            self.assertTrue(a.startswith("Local\\StreamPanel_"))

    def test_mutex_name_differs_for_different_paths(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p1 = Path(d) / "a"
            p2 = Path(d) / "b"
            p1.mkdir()
            p2.mkdir()
            self.assertNotEqual(
                single_instance.mutex_name_for_data_dir(p1),
                single_instance.mutex_name_for_data_dir(p2),
            )


if __name__ == "__main__":
    unittest.main()
