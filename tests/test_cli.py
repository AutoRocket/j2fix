import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from j2fix.cli import main


class CliTests(unittest.TestCase):
    def test_version(self) -> None:
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(output.getvalue(), "j2fix 0.1.0\n")

    def test_check_then_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "test.j2"
            template.write_text("{{value|upper}}\n", encoding="utf-8")
            self.assertEqual(main(["--check", "--no-lint", str(template)]), 1)
            self.assertEqual(main(["--no-lint", str(template)]), 0)
            self.assertEqual(template.read_text(encoding="utf-8"), "{{ value | upper }}\n")
            self.assertEqual(main(["--check", "--no-lint", str(template)]), 0)

    def test_directory_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            (tmp_path / "one.jinja").write_text("{{value}}", encoding="utf-8")
            (tmp_path / "two.txt").write_text("{{value}}", encoding="utf-8")
            self.assertEqual(main(["--no-lint", str(tmp_path)]), 0)
            self.assertEqual((tmp_path / "one.jinja").read_text(encoding="utf-8"), "{{ value }}")
            self.assertEqual((tmp_path / "two.txt").read_text(encoding="utf-8"), "{{value}}")

    def test_formatted_output_passes_official_linter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "test.j2"
            template.write_text("{%if enabled%}\n{{value|upper}}\n{%endif%}\n", encoding="utf-8")
            self.assertEqual(main([str(template)]), 0)
            self.assertEqual(
                template.read_text(encoding="utf-8"),
                "{% if enabled %}\n{{ value | upper }}\n{% endif %}\n",
            )
