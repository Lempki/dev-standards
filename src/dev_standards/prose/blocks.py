"""Splits a block of prose, such as a docstring or a block comment, into paragraphs."""

import re

from .rules import Paragraph, ProseLine

__all__ = ["BANNER", "IGNORE_MARKER", "split_block"]

IGNORE_MARKER = "prose: ignore"

# A comment made only of rule characters, or a label between rules such as "--- Settings ---".
BANNER = re.compile(r"^[-=#*~_ ]*$|^[-=]{2,}\s.*\s[-=]{2,}$")

_FENCE = re.compile(r"^(`{3,}|~{3,})")
_CODE_SECTION = re.compile(r"^(Examples?|Usage):$")


def _indent(text: str) -> int:
    return len(text) - len(text.lstrip())


def split_block(text: str, first_line: int) -> list[Paragraph]:
    """Splits a block of prose into paragraphs on blank lines, skipping code examples.

    Fenced code and doctest examples are not prose.
    Neither are the indented lines under a line that ends with "::" or reads "Example:" or "Usage:".
    A line with the ignore marker is skipped and ends its paragraph.

    Args:
        text: The block's text, one source line per line.
        first_line: The 1-based source line number of the block's first line.

    Returns:
        The paragraphs in order.
    """
    paragraphs: list[Paragraph] = []
    current: Paragraph = []
    in_fence = False
    in_doctest = False
    skip_below: int | None = None
    for offset, raw in enumerate(text.splitlines()):
        stripped = raw.strip()
        indent = _indent(raw)
        if skip_below is not None:
            if not stripped or indent > skip_below:
                continue
            skip_below = None
        if _FENCE.match(stripped):
            in_fence = not in_fence
            continue
        # A doctest example and its expected output run until the next blank line.
        if stripped.startswith(">>>"):
            in_doctest = True
        if in_doctest and stripped:
            continue
        in_doctest = False
        if in_fence:
            continue
        if not stripped or IGNORE_MARKER in stripped:
            if current:
                paragraphs.append(current)
            current = []
            continue
        current.append(ProseLine(first_line + offset, stripped))
        if stripped.endswith("::") or _CODE_SECTION.match(stripped):
            skip_below = indent
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs
