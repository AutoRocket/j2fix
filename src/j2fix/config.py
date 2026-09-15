"""Configuration discovery for j2fix."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
                if "j2fix" in tomllib.load(file).get("tool", {}):
                    return candidate
    return None


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config()
    with path.open("rb") as file:
        data: dict[str, Any] = tomllib.load(file).get("tool", {}).get("j2fix", {})
    extensions = tuple(str(item).lstrip(".") for item in data.get("extensions", Config.extensions))
    exclude = tuple(str(item) for item in data.get("exclude", Config.exclude))
    return Config(
        extensions=extensions,
        exclude=exclude,
        unsafe=bool(data.get("unsafe", False)),
        lint=bool(data.get("lint", True)),
        tab_size=int(data.get("tab_size", 4)),
    )

