import tempfile
import unittest
from pathlib import Path

from j2fix.config import discover_config, load_config


class ConfigTests(unittest.TestCase):
    def test_invalid_config_values_are_rejected(self) -> None:
        for setting in ('unsafe = "false"', "tab_size = -1", 'extensions = "j2"', "unknown = true"):
            with self.subTest(setting=setting), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "pyproject.toml"
                path.write_text("[tool.j2fix]\n" + setting, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_config(path)

    def test_discovery_and_loading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "pyproject.toml"
            path.write_text('[tool.j2fix]\nextensions = [".html"]\nunsafe = true\n', encoding="utf-8")
            child = root / "templates"
            child.mkdir()
            self.assertEqual(discover_config(child), path)
            self.assertEqual(load_config(path).extensions, ("html",))
            self.assertTrue(load_config(path).unsafe)
