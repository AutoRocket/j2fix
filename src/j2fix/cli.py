"""Command-line interface for j2fix."""

from __future__ import annotations

import argparse
import difflib
import logging
import sys
import tempfile
from pathlib import Path

from j2lint.linter.collection import DEFAULT_RULE_DIR, RulesCollection

from . import __version__
from .config import Config, discover_config, load_config
from .formatter import FormatOptions, format_text


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="j2fix", description="Format templates to the Arista j2lint standard")
    parser.add_argument(
        "paths",
        metavar="PATH",
        nargs="*",
        default=["."],
        help="template files or directories; use - for stdin",
    )
    parser.add_argument("--check", action="store_true", help="report files that would change without writing")
    parser.add_argument("--diff", action="store_true", help="print a unified diff without writing")
    parser.add_argument("--unsafe", action="store_true", help="allow render-affecting S6 delimiter fixes")
    parser.add_argument("--no-lint", action="store_true", help="do not run official j2lint rules after formatting")
    parser.add_argument("-c", "--config-file", type=Path, help="pyproject.toml containing [tool.j2fix]")
    parser.add_argument("-e", "--extensions", help="comma-separated extensions")
    parser.add_argument("--version", action="version", version=f"j2fix {__version__}")
    return parser


def _excluded(path: Path, patterns: tuple[str, ...]) -> bool:
    return any(part in patterns for part in path.parts) or any(
        path.match(pattern) for pattern in patterns if any(character in pattern for character in "*?[]")
    )


def _files(paths: list[str], config: Config) -> list[Path]:
    suffixes = {f".{item.lower().lstrip('.')}" for item in config.extensions}
    found: set[Path] = set()
    for value in paths:
        path = Path(value)
        if path.is_file() and path.suffix.lower() in suffixes:
            found.add(path)
        elif path.is_dir():
            found.update(
                item
                for item in path.rglob("*")
                if item.is_file() and item.suffix.lower() in suffixes and not _excluded(item, config.exclude)
            )
    return sorted(found)


def _lint(path: Path) -> list[object]:
    logging.disable(logging.CRITICAL)
    collection = RulesCollection.create_from_directory(DEFAULT_RULE_DIR, [], [])
    errors, _ = collection.run(path)
    return errors


def _show_diff(name: str, old: str, new: str) -> None:
    sys.stdout.writelines(
        difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True), fromfile=name, tofile=name)
    )


def _process_stdin(options: FormatOptions, *, check: bool, diff: bool, lint: bool) -> int:
    original = sys.stdin.read()
    formatted = format_text(original, options)
    if diff:
        _show_diff("stdin.j2", original, formatted)
    elif not check:
        sys.stdout.write(formatted)
    changed = original != formatted
    lint_errors = []
    if lint:
        with tempfile.NamedTemporaryFile("w", suffix=".j2", encoding="utf-8") as file:
            file.write(formatted)
            file.flush()
            lint_errors = _lint(Path(file.name))
    for error in lint_errors:
        print(f"stdin:{error.line_number}: {error.message} ({error.rule.rule_id})", file=sys.stderr)
    return 1 if lint_errors or (check and changed) else 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config_path = args.config_file or discover_config(Path.cwd())
    try:
        config = load_config(config_path)
    except (OSError, ValueError) as error:
        print(f"j2fix: invalid configuration: {error}", file=sys.stderr)
        return 2
    if args.extensions:
        config = Config(tuple(args.extensions.split(",")), config.exclude, config.unsafe, config.lint, config.tab_size)
    options = FormatOptions(unsafe=args.unsafe or config.unsafe, tab_size=config.tab_size)
    lint = config.lint and not args.no_lint

    if args.paths == ["-"]:
        return _process_stdin(options, check=args.check, diff=args.diff, lint=lint)
    if "-" in args.paths:
        print("j2fix: stdin cannot be combined with file paths", file=sys.stderr)
        return 2

    files = _files(args.paths, config)
    if not files:
        print("j2fix: no Jinja2 templates found", file=sys.stderr)
        return 2

    changed_count = 0
    lint_count = 0
    for path in files:
        try:
            original = path.read_text(encoding="utf-8")
            formatted = format_text(original, options)
            changed = original != formatted
            if changed:
                changed_count += 1
                if args.diff:
                    _show_diff(str(path), original, formatted)
                elif args.check:
                    print(f"would reformat {path}")
                else:
                    path.write_text(formatted, encoding="utf-8")
                    print(f"reformatted {path}")

            if lint:
                lint_path = path
                temporary = None
                if (args.check or args.diff) and changed:
                    temporary = tempfile.NamedTemporaryFile("w", suffix=path.suffix, encoding="utf-8")
                    temporary.write(formatted)
                    temporary.flush()
                    lint_path = Path(temporary.name)
                errors = _lint(lint_path)
                if temporary:
                    temporary.close()
                lint_count += len(errors)
                for error in errors:
                    print(f"{path}:{error.line_number}: {error.message} ({error.rule.rule_id})", file=sys.stderr)
        except OSError as error:
            print(f"j2fix: {path}: {error}", file=sys.stderr)
            return 2

    if changed_count == 0 and lint_count == 0:
        print(f"{len(files)} file(s) already formatted")
    elif lint_count:
        print(f"j2fix: {lint_count} unfixable j2lint issue(s) remain", file=sys.stderr)
    return 1 if lint_count or ((args.check or args.diff) and changed_count) else 0
