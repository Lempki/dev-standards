"""The sync-files hook.

Keeps the canonical configuration files identical across repositories.
Each target is built from a shared part and a part per language.
A repository gets the parts of its own languages.
Whole-file targets must match exactly.
Block targets must contain the canonical managed block.
Lines outside the managed block belong to the repository.
"""

from dataclasses import dataclass
from enum import Enum
from importlib.resources import files
from pathlib import Path

__all__ = [
    "BLOCK_END",
    "BLOCK_START",
    "Mode",
    "Part",
    "Result",
    "Target",
    "TARGETS",
    "sync",
]

BLOCK_START = "# >>> dev-standards managed block. Change it in dev-standards."
BLOCK_END = "# <<< dev-standards managed block."


class Mode(Enum):
    """How a canonical file is applied to its target."""

    WHOLE = "whole"
    BLOCK = "block"


class Result(Enum):
    """The state of one target after a sync or check."""

    OK = "up to date"
    CHANGED = "updated"
    OUTDATED = "out of date"
    SKIPPED = "skipped"
    UNUSED = "not used by this repository's languages"


@dataclass(frozen=True)
class Part:
    """One canonical file that makes up part of a target.

    Attributes:
        source: The file name in the canonical folder.
        language: The language that needs the part, or None for a part every repository gets.
    """

    source: str
    language: str | None = None


@dataclass(frozen=True)
class Target:
    """A repository path and the canonical parts it is built from.

    Attributes:
        path: The file's path in the repository.
        mode: Whether the parts make up the whole file or a managed block in it.
        parts: The canonical parts, in the order they appear.
        legacy_marker: A line that marks a copy from when the target was a whole managed file.
            sync replaces such a copy entirely instead of keeping it as the repository's own lines.
    """

    path: str
    mode: Mode
    parts: tuple[Part, ...]
    legacy_marker: str | None = None


TARGETS = (
    Target(
        ".editorconfig",
        Mode.BLOCK,
        (Part("editorconfig"), Part("editorconfig.lua", "lua")),
        legacy_marker="# This file is managed by dev-standards. Change it there, not here.",
    ),
    Target(".ruff-base.toml", Mode.WHOLE, (Part("ruff-base.toml", "python"),)),
    Target(".gitattributes", Mode.BLOCK, (Part("gitattributes.block"),)),
    Target(
        ".gitignore",
        Mode.BLOCK,
        (Part("gitignore.block"), Part("gitignore.python.block", "python")),
    ),
)


def _canonical(name: str) -> str:
    return (
        files("dev_standards").joinpath("canonical", name).read_text(encoding="utf-8")
    )


def _content(target: Target, languages: tuple[str, ...]) -> str | None:
    """Joins the parts that the languages need, or returns None when the target needs none.

    A target whose parts all belong to other languages is not used.
    """
    parts = [
        part
        for part in target.parts
        if part.language is None or part.language in languages
    ]
    if not parts:
        return None
    # A blank line separates the parts, as it separates sections in each of these files.
    return "\n".join(_canonical(part.source).rstrip("\n") + "\n" for part in parts)


def _with_block(current: str, block: str) -> str:
    """Returns current with its managed block replaced, or prepended when absent."""
    managed = f"{BLOCK_START}\n{block.rstrip()}\n{BLOCK_END}\n"
    lines = current.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip() == BLOCK_START]
    ends = [i for i, line in enumerate(lines) if line.rstrip() == BLOCK_END]
    if starts and ends and ends[0] > starts[0]:
        before = "".join(lines[: starts[0]])
        after = "".join(lines[ends[0] + 1 :])
        return before + managed + after
    rest = current.lstrip("\n")
    return managed + ("\n" + rest if rest else "")


def _expected(target: Target, current: str, content: str) -> str:
    if target.mode is Mode.WHOLE:
        return content
    lines = {line.rstrip() for line in current.splitlines()}
    legacy = target.legacy_marker is not None and target.legacy_marker in lines
    if legacy and BLOCK_START not in lines:
        # The whole file came from dev-standards, so none of it is the repository's own.
        current = ""
    return _with_block(current, content)


def sync(
    root: Path,
    *,
    fix: bool,
    languages: tuple[str, ...],
    skip: tuple[str, ...] = (),
) -> dict[str, Result]:
    """Checks, and optionally updates, every canonical target in a repository.

    Args:
        root: The repository root.
        fix: Whether to write the expected content when a target is out of date.
        languages: The repository's languages, which pick the canonical parts it gets.
        skip: Target paths the repository opts out of.

    Returns:
        The result for each target path.
    """
    results: dict[str, Result] = {}
    for target in TARGETS:
        if target.path in skip:
            results[target.path] = Result.SKIPPED
            continue
        content = _content(target, languages)
        if content is None:
            # An old copy, from before the languages counted, is left for the repository to delete.
            results[target.path] = Result.UNUSED
            continue
        path = root / target.path
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        expected = _expected(target, current, content)
        if current == expected:
            results[target.path] = Result.OK
        elif fix:
            path.write_text(expected, encoding="utf-8", newline="\n")
            results[target.path] = Result.CHANGED
        else:
            results[target.path] = Result.OUTDATED
    return results
