"""The check-prose hook.

Enforces the prose rules on Python comments, Python docstrings, and Markdown.
"""

from fnmatch import fnmatch
from pathlib import Path

from ..config import ProseConfig
from . import markdown, python_source
from .rules import Violation, check_paragraph

__all__ = ["Violation", "check_file", "check_paths"]

_MARKDOWN_SUFFIXES = {".md", ".markdown"}


def check_file(path: Path, source: str, config: ProseConfig) -> list[Violation]:
    """Checks the prose of one file.

    Args:
        path: The file path, used to pick the extractor and in the report.
        source: The file contents.
        config: The prose settings of the repository.

    Returns:
        The violations found, in line order. Unsupported file types yield none.
    """
    if path.suffix == ".py":
        paragraphs = python_source.extract_paragraphs(source)
        limit = config.python_max_em_dashes
    elif path.suffix in _MARKDOWN_SUFFIXES:
        paragraphs = markdown.extract_paragraphs(source)
        limit = config.markdown_max_em_dashes
    else:
        return []
    violations: list[Violation] = []
    for paragraph in paragraphs:
        violations.extend(check_paragraph(path, paragraph, limit))
    return sorted(violations)


def _is_excluded(path: Path, root: Path, patterns: tuple[str, ...]) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        relative = path.as_posix()
    return any(fnmatch(relative, pattern) for pattern in patterns)


def check_paths(paths: list[Path], root: Path, config: ProseConfig) -> list[Violation]:
    """Checks the prose of several files, honoring the exclude patterns.

    Args:
        paths: The files to check.
        root: The repository root that exclude patterns are relative to.
        config: The prose settings of the repository.

    Returns:
        All violations, in file and line order.
    """
    violations: list[Violation] = []
    for path in paths:
        if _is_excluded(path, root, config.exclude):
            continue
        source = path.read_text(encoding="utf-8")
        violations.extend(check_file(path, source, config))
    return violations
