"""The sync-files hook.

Keeps the canonical configuration files identical across repositories.
Whole-file targets must match exactly.
Block targets must contain the canonical managed block.
Lines outside the managed block belong to the repository.
"""

from dataclasses import dataclass
from enum import Enum
from importlib.resources import files
from pathlib import Path

__all__ = ["BLOCK_END", "BLOCK_START", "Mode", "Result", "Target", "TARGETS", "sync"]

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


@dataclass(frozen=True)
class Target:
    """A canonical file and the repository path it is applied to."""

    source: str
    path: str
    mode: Mode


TARGETS = (
    Target("editorconfig", ".editorconfig", Mode.WHOLE),
    Target("ruff-base.toml", ".ruff-base.toml", Mode.WHOLE),
    Target("gitattributes.block", ".gitattributes", Mode.BLOCK),
    Target("gitignore.block", ".gitignore", Mode.BLOCK),
)


def _canonical(name: str) -> str:
    return (
        files("dev_standards").joinpath("canonical", name).read_text(encoding="utf-8")
    )


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


def _expected(target: Target, current: str) -> str:
    canonical = _canonical(target.source)
    if target.mode is Mode.WHOLE:
        return canonical
    return _with_block(current, canonical)


def sync(root: Path, *, fix: bool, skip: tuple[str, ...] = ()) -> dict[str, Result]:
    """Checks, and optionally updates, every canonical target in a repository.

    Args:
        root: The repository root.
        fix: Whether to write the expected content when a target is out of date.
        skip: Target paths the repository opts out of.

    Returns:
        The result for each target path.
    """
    results: dict[str, Result] = {}
    for target in TARGETS:
        if target.path in skip:
            results[target.path] = Result.SKIPPED
            continue
        path = root / target.path
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        expected = _expected(target, current)
        if current == expected:
            results[target.path] = Result.OK
        elif fix:
            path.write_text(expected, encoding="utf-8", newline="\n")
            results[target.path] = Result.CHANGED
        else:
            results[target.path] = Result.OUTDATED
    return results
