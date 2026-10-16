"""Extracts comment paragraphs from Lua source."""

import re
from dataclasses import dataclass

from .blocks import BANNER, IGNORE_MARKER, split_block
from .rules import Paragraph, ProseLine

__all__ = ["extract_paragraphs"]

# luacheck options, LuaLS annotations such as "---@param", and formatter switches are not prose.
_PRAGMA = re.compile(r"^(luacheck:|@|stylua:|format:)")
_LONG_BRACKET = re.compile(r"\[(=*)\[")


@dataclass(frozen=True)
class _LineComment:
    line: int
    column: int
    text: str
    full_line: bool


@dataclass(frozen=True)
class _BlockComment:
    line: int
    text: str


def _skip_quoted(source: str, start: int) -> int:
    """Returns the index just past the quoted string that opens at start."""
    quote = source[start]
    index = start + 1
    while index < len(source):
        char = source[index]
        if char == "\\":
            index += 2
            continue
        if char == quote or char == "\n":
            return index + 1
        index += 1
    return index


def _long_bracket_end(source: str, start: int, level: str) -> int:
    """Returns the index just past the matching long bracket close, or the end of source."""
    closer = "]" + level + "]"
    end = source.find(closer, start)
    return len(source) if end == -1 else end + len(closer)


def _scan(source: str) -> tuple[list[_LineComment], list[_BlockComment]]:
    """Finds every comment, skipping string literals and long strings."""
    line_comments: list[_LineComment] = []
    block_comments: list[_BlockComment] = []
    index = 0
    line = 1
    line_start = 0
    # A shebang line is not a comment in Lua, and not prose either.
    if source.startswith("#"):
        index = source.find("\n")
        index = len(source) if index == -1 else index
    while index < len(source):
        char = source[index]
        if char == "\n":
            line += 1
            index += 1
            line_start = index
            continue
        if char in "\"'":
            index = _skip_quoted(source, index)
            continue
        if char == "[":
            bracket = _LONG_BRACKET.match(source, index)
            if bracket:
                end = _long_bracket_end(source, bracket.end(), bracket.group(1))
                line += source.count("\n", index, end)
                line_start = source.rfind("\n", 0, end) + 1
                index = end
                continue
        if source.startswith("--", index):
            bracket = _LONG_BRACKET.match(source, index + 2)
            if bracket:
                end = _long_bracket_end(source, bracket.end(), bracket.group(1))
                body_end = end - len(bracket.group(1)) - 2
                text = source[bracket.end() : max(bracket.end(), body_end)]
                block_comments.append(_BlockComment(line, text))
                line += source.count("\n", index, end)
                line_start = source.rfind("\n", 0, end) + 1
                index = end
                continue
            end = source.find("\n", index)
            end = len(source) if end == -1 else end
            full_line = source[line_start:index].strip() == ""
            line_comments.append(
                _LineComment(
                    line, index - line_start, source[index + 2 : end], full_line
                )
            )
            index = end
            continue
        index += 1
    return line_comments, block_comments


def _is_banner(raw: str) -> bool:
    """True for a comment made only of rule characters, or a label between rules."""
    return bool(BANNER.match(raw.strip()) or BANNER.match(raw.lstrip("-").strip()))


def _comment_text(raw: str) -> str | None:
    """Returns the prose of a line comment, or None when it is not prose."""
    # LDoc and LuaLS comments start with "---", which is the same prose.
    text = raw.lstrip("-")
    text = text[1:] if text.startswith((" ", "\t")) else text
    stripped = text.strip()
    if _is_banner(raw):
        return None
    if _PRAGMA.match(stripped):
        return None
    # A single word is a section label such as "-- helpers", not a sentence.
    if len(stripped.split()) == 1:
        return None
    if IGNORE_MARKER in stripped:
        return None
    return text.rstrip()


def _adjacent(first: _LineComment | None, second: _LineComment | None) -> bool:
    """True when two full-line comments sit on consecutive lines at the same column."""
    return (
        first is not None
        and second is not None
        and first.full_line
        and second.full_line
        and first.line == second.line - 1
        and first.column == second.column
    )


def _is_heading(comments: list[_LineComment], index: int) -> bool:
    """True for a line between two rules, such as "-- Public API" between "-- ####" lines."""
    if index == 0 or index + 1 >= len(comments):
        return False
    before, line, after = comments[index - 1], comments[index], comments[index + 1]
    return (
        _adjacent(before, line)
        and _adjacent(line, after)
        and _is_banner(before.text)
        and _is_banner(after.text)
    )


def _line_paragraphs(comments: list[_LineComment]) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    current: Paragraph = []
    previous: _LineComment | None = None
    for index, comment in enumerate(comments):
        continues = _adjacent(previous, comment) and bool(current)
        text = None if _is_heading(comments, index) else _comment_text(comment.text)
        if not continues or text is None or not text.strip():
            if current:
                paragraphs.append(current)
            current = []
        if text is not None and text.strip():
            current.append(ProseLine(comment.line, text))
            if not comment.full_line:
                paragraphs.append(current)
                current = []
        previous = comment if comment.full_line else None
    if current:
        paragraphs.append(current)
    return paragraphs


def _block_paragraphs(comment: _BlockComment) -> list[Paragraph]:
    """Splits a block comment into paragraphs.

    A block whose first line carries the ignore marker is skipped whole, such as commented-out code.
    """
    first_line = comment.text.split("\n", 1)[0]
    if IGNORE_MARKER in first_line:
        return []
    # A block often closes with "--]]", which leaves a "--" line inside its text.
    # That form lets the block be uncommented by deleting one dash.
    text = re.sub(r"\n[ \t]*--[ \t]*$", "\n", comment.text)
    return split_block(text, comment.line)


def extract_paragraphs(source: str) -> list[Paragraph]:
    """Extracts every prose paragraph from Lua source.

    Line comment blocks are consecutive full-line comments at the same column.
    A trailing comment after code is a paragraph of its own.
    Block comments are split on blank lines, like Python docstrings.
    Strings and long strings are skipped, so "--" inside them is never a comment.

    Args:
        source: The contents of a Lua file.

    Returns:
        The paragraphs in source order.
    """
    line_comments, block_comments = _scan(source)
    paragraphs = _line_paragraphs(line_comments)
    for comment in block_comments:
        paragraphs.extend(_block_paragraphs(comment))
    return sorted(paragraphs, key=lambda paragraph: paragraph[0].line)
