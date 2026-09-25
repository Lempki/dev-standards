"""Reads the [tool.dev-standards] table from a repository's pyproject.toml."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "ConfigError",
    "ProseConfig",
    "Settings",
    "SyncConfig",
    "TemplateConfig",
    "load_settings",
]


class ConfigError(Exception):
    """Raised when the [tool.dev-standards] table holds an invalid value."""


@dataclass(frozen=True)
class ProseConfig:
    """Settings for the check-prose hook.

    Attributes:
        exclude: Glob patterns, relative to the repository root, that are never checked.
        python_max_em_dashes: Em dashes allowed per comment block or docstring paragraph.
        markdown_max_em_dashes: Em dashes allowed per Markdown paragraph or list item.
    """

    exclude: tuple[str, ...] = ()
    python_max_em_dashes: int = 0
    markdown_max_em_dashes: int = 1


@dataclass(frozen=True)
class SyncConfig:
    """Settings for the sync-files hook.

    Attributes:
        skip: Canonical target paths this repository opts out of.
    """

    skip: tuple[str, ...] = ()


@dataclass(frozen=True)
class TemplateConfig:
    """Settings that link a repository to the template it was created from.

    Attributes:
        package: The import package name that replaces {package} in manifest paths.
        ignore: Manifest paths this repository deliberately diverges on.
    """

    package: str | None = None
    ignore: tuple[str, ...] = ()


@dataclass(frozen=True)
class Settings:
    """All dev-standards settings of one repository."""

    prose: ProseConfig = field(default_factory=ProseConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)
    template: TemplateConfig = field(default_factory=TemplateConfig)


def _strings(table: dict[str, Any], key: str) -> tuple[str, ...]:
    value = table.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"'{key}' must be a list of strings.")
    return tuple(value)


def _int(table: dict[str, Any], key: str, default: int) -> int:
    value = table.get(key, default)
    if not isinstance(value, int) or value < 0:
        raise ConfigError(f"'{key}' must be a non-negative integer.")
    return value


def load_settings(root: Path) -> Settings:
    """Loads the dev-standards settings of the repository at root.

    A missing pyproject.toml or a missing table yields the defaults.

    Args:
        root: The repository root directory.

    Returns:
        The parsed settings.

    Raises:
        ConfigError: If a known key holds a value of the wrong type.
    """
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return Settings()
    with pyproject.open("rb") as file:
        data = tomllib.load(file)
    table = data.get("tool", {}).get("dev-standards", {})
    prose = table.get("prose", {})
    sync = table.get("sync", {})
    template = table.get("template", {})
    package = template.get("package")
    if package is not None and not isinstance(package, str):
        raise ConfigError("'package' must be a string.")
    return Settings(
        prose=ProseConfig(
            exclude=_strings(prose, "exclude"),
            python_max_em_dashes=_int(prose, "python-max-em-dashes", 0),
            markdown_max_em_dashes=_int(prose, "markdown-max-em-dashes", 1),
        ),
        sync=SyncConfig(skip=_strings(sync, "skip")),
        template=TemplateConfig(package=package, ignore=_strings(template, "ignore")),
    )
