import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from j2fix import __version__
from j2fix.cli import main


class CliTests(unittest.TestCase):
    def test_version(self) -> None:
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(output.getvalue(), f"j2fix {__version__}\n")

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

    def test_stdin_diff_returns_nonzero(self) -> None:
        output = StringIO()
        with patch("sys.stdin", StringIO("{{value}}\n")), redirect_stdout(output):
            self.assertEqual(main(["--diff", "--no-lint", "-"]), 1)
        self.assertIn("+{{ value }}", output.getvalue())

    def test_diff_without_final_newline(self) -> None:
        output = StringIO()
        with patch("sys.stdin", StringIO("{{value}}")), redirect_stdout(output):
            self.assertEqual(main(["--diff", "--no-lint", "-"]), 1)
        self.assertIn("-{{value}}\n\\ No newline at end of file\n+{{ value }}\n", output.getvalue())

    def test_crlf_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "test.j2"
            template.write_bytes(b"{{value}}\r\n")
            self.assertEqual(main(["--no-lint", str(template)]), 0)
            self.assertEqual(template.read_bytes(), b"{{ value }}\r\n")

    def test_invalid_template_is_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as directory, redirect_stderr(StringIO()):
            template = Path(directory) / "test.j2"
            source = b"{%if value%}\n{{value}}\n"
            template.write_bytes(source)
            self.assertEqual(main([str(template)]), 1)
            self.assertEqual(template.read_bytes(), source)

    def test_missing_input_is_an_error_even_alongside_valid_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory, redirect_stderr(StringIO()):
            template = Path(directory) / "test.j2"
            template.write_text("{{value}}", encoding="utf-8")
            self.assertEqual(main([str(template), str(Path(directory) / "missing.j2")]), 2)
            self.assertEqual(template.read_text(encoding="utf-8"), "{{value}}")

    def test_malformed_discovered_config_has_friendly_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory, redirect_stderr(StringIO()):
            (Path(directory) / "pyproject.toml").write_text("[tool.j2fix", encoding="utf-8")
            with patch("j2fix.cli.Path.cwd", return_value=Path(directory)):
                self.assertEqual(main([directory]), 2)
