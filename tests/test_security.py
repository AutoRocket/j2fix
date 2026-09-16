"""Regression tests for hostile input and failures during file replacement."""

import os
import stat
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from j2fix import FormatOptions, TemplateLimitError, format_text
from j2fix.cli import _files, main
from j2fix.config import Config, discover_config, load_config
from j2fix.files import _DIR_FD, open_template
from j2fix.limits import MAX_INPUT_BYTES, MAX_NESTING, MAX_TOKENS


@pytest.mark.parametrize(
    "source",
    [
        "{{ " + "(" * 150 + "1" + ")" * 150 + " }}",
        "{% if true %}" * (MAX_NESTING + 1) + "{% endif %}" * (MAX_NESTING + 1),
        "{% set capture %}" * (MAX_NESTING + 1) + "{% endset %}" * (MAX_NESTING + 1),
    ],
)
def test_deep_input_is_rejected_by_api(source):
    with pytest.raises(TemplateLimitError, match="nesting"):
        format_text(source)


def test_token_budget():
    with pytest.raises(TemplateLimitError, match="token"):
        format_text("{{x}}" * (MAX_TOKENS // 3 + 1))


def test_parser_recursion_becomes_controlled_error():
    with patch("j2fix.formatter.Environment.parse", side_effect=RecursionError):
        with pytest.raises(TemplateLimitError, match="too complex"):
            format_text("{{x}}")


@pytest.mark.parametrize("source", ["a" * (MAX_INPUT_BYTES + 1), "é" * (MAX_INPUT_BYTES // 2 + 1)])
def test_byte_limit_applies_to_api_and_stdin(source, monkeypatch, capsys):
    with pytest.raises(TemplateLimitError, match="byte"):
        format_text(source)
    monkeypatch.setattr("sys.stdin", StringIO(source))
    assert main(["--no-lint", "-"]) == 2
    captured = capsys.readouterr()
    assert "byte limit" in captured.err
    assert not captured.out


def test_stdin_read_is_bounded(monkeypatch):
    class BoundedInput(StringIO):
        def read(self, size=-1):
            assert size == MAX_INPUT_BYTES + 1
            return super().read(size)

    monkeypatch.setattr("sys.stdin", BoundedInput("{{value}}"))
    assert main(["--no-lint", "-"]) == 0


def test_stdin_complexity_has_friendly_error(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", StringIO("{{ " + "(" * 150 + "1" + ")" * 150 + " }}"))
    assert main(["--check", "--no-lint", "-"]) == 2
    captured = capsys.readouterr()
    assert "nesting limit" in captured.err
    assert "Traceback" not in captured.err
    assert not captured.out


def test_comments_raw_and_strings_do_not_count_as_nesting():
    value = "(" * 151
    for source in (f"{{{{ '{value}' }}}}", "{# " + value + " #}", "{% raw %}" + value + "{% endraw %}"):
        assert format_text(source) == source


def test_oversize_file_is_not_read_or_changed(tmp_path):
    path = tmp_path / "large.j2"
    source = b"a" * (MAX_INPUT_BYTES + 1)
    path.write_bytes(source)
    assert main(["--no-lint", str(path)]) == 2
    assert path.read_bytes() == source


def test_bad_file_does_not_prevent_processing_other_files(tmp_path):
    bad = tmp_path / "a.j2"
    good = tmp_path / "b.j2"
    source = "{{ " + "(" * 150 + "1" + ")" * 150 + " }}"
    bad.write_text(source)
    good.write_text("{{value}}")
    assert main(["--no-lint", str(tmp_path)]) == 2
    assert bad.read_text() == source
    assert good.read_text() == "{{ value }}"


@pytest.mark.parametrize("tab_size", [0, -1, 17, 1_000_000_000, True, "4"])
def test_tab_size_is_bounded(tab_size):
    with pytest.raises(ValueError, match="between"):
        FormatOptions(tab_size=tab_size)


@pytest.mark.parametrize("source", ['tool = "not a table"', "tool = 42"])
def test_invalid_tool_table_is_reported(tmp_path, source):
    config = tmp_path / "pyproject.toml"
    config.write_text(source)
    for load in (lambda: discover_config(tmp_path), lambda: load_config(config)):
        with pytest.raises(ValueError, match="tool must be a TOML table"):
            load()
    assert main(["--config-file", str(config), str(tmp_path)]) == 2


def make_link(link: Path, target: Path):
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")


def test_directory_discovery_skips_links_and_exclusions(tmp_path):
    outside = tmp_path / "outside.j2"
    outside.write_text("{{value}}")
    templates = tmp_path / "templates"
    templates.mkdir()
    good = templates / "good.j2"
    good.write_text("{{value}}")
    make_link(templates / "linked.j2", outside)
    make_link(templates / "linked-dir", tmp_path)
    ignored = templates / ".venv"
    ignored.mkdir()
    (ignored / "ignored.j2").write_text("{{value}}")
    assert _files([str(templates)], Config()) == [good]
    assert main(["--no-lint", str(templates)]) == 0
    assert outside.read_text() == "{{value}}"
    assert (ignored / "ignored.j2").read_text() == "{{value}}"


def test_explicit_link_and_linked_parent_are_rejected(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    path = real / "test.j2"
    path.write_text("{{value}}")
    make_link(tmp_path / "linked.j2", path)
    make_link(tmp_path / "linked-dir", real)
    for candidate in (tmp_path / "linked.j2", tmp_path / "linked-dir", tmp_path / "linked-dir" / "test.j2"):
        assert main(["--no-lint", str(candidate)]) == 2
    assert path.read_text() == "{{value}}"


@pytest.mark.parametrize("operation", ["fsync", "replace"])
def test_write_failure_preserves_original_and_cleans_temp(tmp_path, operation):
    path = tmp_path / "test.j2"
    source = b"{{value}}\r\n"
    path.write_bytes(source)
    with patch(f"j2fix.files.os.{operation}", side_effect=OSError("simulated disk failure")):
        assert main(["--no-lint", str(path)]) == 2
    assert path.read_bytes() == source
    assert list(tmp_path.iterdir()) == [path]


def test_linter_crash_does_not_write(tmp_path):
    path = tmp_path / "test.j2"
    path.write_text("{{value}}")
    with patch("j2fix.cli._lint", side_effect=RecursionError("too complex")):
        assert main([str(path)]) == 2
    assert path.read_text() == "{{value}}"


def test_concurrent_edit_is_not_overwritten(tmp_path):
    path = tmp_path / "test.j2"
    path.write_text("{{value}}")
    with open_template(path) as file:
        file.read()
        path.write_text("new user content")
        with pytest.raises(OSError, match="changed"):
            file.replace("{{ value }}")
    assert path.read_text() == "new user content"
    assert list(tmp_path.iterdir()) == [path]


def test_symlink_swap_before_read_is_rejected(tmp_path):
    path = tmp_path / "test.j2"
    outside = tmp_path / "outside.j2"
    path.write_text("{{value}}")
    outside.write_text("{{secret}}")
    with open_template(path) as file:
        path.unlink()
        make_link(path, outside)
        with pytest.raises(OSError):
            file.read()
    assert outside.read_text() == "{{secret}}"


def test_symlink_swap_before_write_is_rejected(tmp_path):
    path = tmp_path / "test.j2"
    outside = tmp_path / "outside.j2"
    path.write_text("{{value}}")
    outside.write_text("{{secret}}")
    with open_template(path) as file:
        file.read()
        path.unlink()
        make_link(path, outside)
        with pytest.raises(OSError):
            file.replace("{{ value }}")
    assert outside.read_text() == "{{secret}}"
    assert path.is_symlink()
    assert not list(tmp_path.glob(".j2fix-*.tmp"))


@pytest.mark.skipif(not _DIR_FD, reason="requires directory-descriptor support")
def test_parent_swap_cannot_redirect_write(tmp_path):
    parent = tmp_path / "templates"
    parent.mkdir()
    path = parent / "test.j2"
    path.write_text("{{value}}")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "test.j2").write_text("{{secret}}")
    with open_template(path) as file:
        file.read()
        parent.rename(tmp_path / "renamed")
        make_link(parent, outside)
        file.replace("{{ value }}")
    assert (outside / "test.j2").read_text() == "{{secret}}"
    assert (tmp_path / "renamed" / "test.j2").read_text() == "{{ value }}"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits")
def test_file_permissions_are_preserved(tmp_path):
    path = tmp_path / "test.j2"
    path.write_text("{{value}}")
    path.chmod(0o640)
    assert main(["--no-lint", str(path)]) == 0
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits")
def test_read_only_file_is_not_replaced(tmp_path):
    path = tmp_path / "test.j2"
    path.write_text("{{value}}")
    path.chmod(0o400)
    try:
        assert main(["--no-lint", str(path)]) == 2
        assert path.read_text() == "{{value}}"
    finally:
        path.chmod(0o600)


def test_output_expansion_is_bounded(tmp_path):
    path = tmp_path / "test.j2"
    source = " " * (MAX_INPUT_BYTES - len("{{x}}")) + "{{x}}"
    path.write_text(source)
    assert main(["--no-lint", str(path)]) == 2
    assert path.read_text() == source


@pytest.mark.skipif(not hasattr(os, "link"), reason="hardlinks unavailable")
def test_atomic_replacement_does_not_modify_hardlinked_copy(tmp_path):
    path = tmp_path / "test.j2"
    other = tmp_path / "copy.j2"
    path.write_text("{{value}}")
    os.link(path, other)
    assert main(["--no-lint", str(path)]) == 0
    assert path.read_text() == "{{ value }}"
    assert other.read_text() == "{{value}}"


def test_portable_file_handling(tmp_path):
    path = tmp_path / "test.j2"
    path.write_bytes(b"{{value}}\r\n")
    with patch("j2fix.files._DIR_FD", False):
        assert main(["--no-lint", str(path)]) == 0
    assert path.read_bytes() == b"{{ value }}\r\n"
