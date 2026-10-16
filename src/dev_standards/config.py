"""Reads a repository's dev-standards settings and tells which languages it uses.

A Python repository keeps them in the [tool.dev-standards] table of its pyproject.toml.
A repository without a pyproject.toml, such as a Lua one, uses dev-standards.toml instead.
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "LANGUAGE_MARKERS",
    "LANGUAGES",
    "ConfigError",
    "ProseConfig",
    "Settings",
    "SyncConfig",
    "SETTINGS_FILE",
    "TemplateConfig",
    "load_settings",
    "repository_languages",
]

SETTINGS_FILE = "dev-standards.toml"

# The languages that dev-standards has canonical files for.
LANGUAGES = ("python", "lua")

# A file at the repository root that shows that the repository uses a language.
LANGUAGE_MARKERS = {"python": "pyproject.toml", "lua": ".luacheckrc"}


class ConfigError(Exception):
    """Raised when the [tool.dev-standards] table holds an invalid value."""


@dataclass(frozen=True)
class ProseConfig:
    """Settings for the check-prose hook.

    Attributes:
        exclude: Glob patterns, relative to the repository root, that are never checked.
        python_max_em_dashes: Em dashes allowed per comment block or docstring paragraph.
        lua_max_em_dashes: Em dashes allowed per Lua comment block or block comment paragraph.
        markdown_max_em_dashes: Em dashes allowed per Markdown paragraph or list item.
    """

    exclude: tuple[str, ...] = ()
    python_max_em_dashes: int = 0
    lua_max_em_dashes: int = 0
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
    """All dev-standards settings of one repository.

    Attributes:
        languages: The languages that the repository declares, or None to detect them.
        prose: The check-prose settings.
        sync: The sync-files settings.
        template: The template-check settings.
    """

    languages: tuple[str, ...] | None = None
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


def _load_table(root: Path) -> dict[str, Any]:
    """Returns the settings table from pyproject.toml or dev-standards.toml, or an empty one."""
    table: dict[str, Any] | None = None
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        with pyproject.open("rb") as file:
            table = tomllib.load(file).get("tool", {}).get("dev-standards")
    standalone = root / SETTINGS_FILE
    if standalone.is_file():
        if table is not None:
            raise ConfigError(
                f"Settings are in both pyproject.toml and {SETTINGS_FILE}. Keep one."
            )
        with standalone.open("rb") as file:
            table = tomllib.load(file)
    return table or {}


def load_settings(root: Path) -> Settings:
    """Loads the dev-standards settings of the repository at root.

    No settings file, or no table in pyproject.toml, yields the defaults.

    Args:
        root: The repository root directory.

    Returns:
        The parsed settings.

    Raises:
        ConfigError: If a known key holds a value of the wrong type, or both files hold settings.
    """
    table = _load_table(root)
    languages = None
    if "languages" in table:
        languages = _strings(table, "languages")
        unknown = sorted(set(languages) - set(LANGUAGES))
        if unknown:
            raise ConfigError(
                f"Unknown language(s): {', '.join(unknown)}. "
                f"dev-standards knows {', '.join(LANGUAGES)}."
            )
    prose = table.get("prose", {})
    sync = table.get("sync", {})
    template = table.get("template", {})
    package = template.get("package")
    if package is not None and not isinstance(package, str):
        raise ConfigError("'package' must be a string.")
    return Settings(
        languages=languages,
        prose=ProseConfig(
            exclude=_strings(prose, "exclude"),
            python_max_em_dashes=_int(prose, "python-max-em-dashes", 0),
            lua_max_em_dashes=_int(prose, "lua-max-em-dashes", 0),
            markdown_max_em_dashes=_int(prose, "markdown-max-em-dashes", 1),
        ),
        sync=SyncConfig(skip=_strings(sync, "skip")),
        template=TemplateConfig(package=package, ignore=_strings(template, "ignore")),
    )


def repository_languages(root: Path, settings: Settings) -> tuple[str, ...]:
    """Returns the languages of the repository at root, as declared or detected.

    A declared list wins, even an empty one for a repository without code.
    Otherwise each language whose marker file is at the root counts.

    Args:
        root: The repository root directory.
        settings: The repository's settings, which may declare the languages.

    Returns:
        The languages, in the order of LANGUAGES when detected.

    Raises:
        ConfigError: If nothing is declared and no marker file is found.
    """
    if settings.languages is not None:
        return settings.languages
    found = tuple(
        language
        for language in LANGUAGES
        if (root / LANGUAGE_MARKERS[language]).is_file()
    )
    if not found:
        markers = ", ".join(
            f"{name} for {lang}" for lang, name in LANGUAGE_MARKERS.items()
        )
        raise ConfigError(
            f"Cannot tell this repository's languages from its files ({markers}). "
            f'Declare them in {SETTINGS_FILE}, such as languages = ["lua"].'
        )
    return found
