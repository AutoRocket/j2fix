"""Configuration discovery for j2fix."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .limits import MAX_TAB_SIZE

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib


@dataclass(frozen=True)
class Config:
    extensions: tuple[str, ...] = ("j2", "jinja", "jinja2")
    exclude: tuple[str, ...] = (".git", ".venv", "venv", "build", "dist")
    unsafe: bool = False
    lint: bool = True
    tab_size: int = 4


def discover_config(start: Path) -> Path | None:
    current = start.resolve() if start.is_dir() else start.resolve().parent
    for directory in (current, *current.parents):
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            with candidate.open("rb") as file:
                tool = tomllib.load(file).get("tool", {})
                if not isinstance(tool, dict):
                    raise ValueError("tool must be a TOML table")
                if "j2fix" in tool:
                    return candidate
    return None


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config()
    with path.open("rb") as file:
        tool = tomllib.load(file).get("tool", {})
    if not isinstance(tool, dict):
        raise ValueError("tool must be a TOML table")
    data: dict[str, Any] = tool.get("j2fix", {})
    if not isinstance(data, dict):
        raise ValueError("tool.j2fix must be a TOML table")
    unknown = data.keys() - Config.__dataclass_fields__.keys()
    if unknown:
        raise ValueError(f"unknown setting(s): {', '.join(sorted(unknown))}")
    for name in ("extensions", "exclude"):
        if name in data and (
            not isinstance(data[name], list) or not all(isinstance(item, str) and item for item in data[name])
        ):
            raise ValueError(f"{name} must be an array of non-empty strings")
    for name in ("unsafe", "lint"):
        if name in data and type(data[name]) is not bool:
            raise ValueError(f"{name} must be a boolean")
    if "tab_size" in data and (type(data["tab_size"]) is not int or not 1 <= data["tab_size"] <= MAX_TAB_SIZE):
        raise ValueError(f"tab_size must be an integer between 1 and {MAX_TAB_SIZE}")
    extensions = tuple(str(item).lstrip(".") for item in data.get("extensions", Config.extensions))
    exclude = tuple(str(item) for item in data.get("exclude", Config.exclude))
    return Config(
        extensions=extensions,
        exclude=exclude,
        unsafe=bool(data.get("unsafe", False)),
        lint=bool(data.get("lint", True)),
        tab_size=int(data.get("tab_size", 4)),
    )
