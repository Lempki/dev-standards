"""Extracts comment and docstring paragraphs from Python source."""

import ast
import io
import re
import tokenize

from .blocks import BANNER, IGNORE_MARKER, split_block
from .rules import Paragraph, ProseLine

__all__ = ["IGNORE_MARKER", "extract_paragraphs"]

_PRAGMA = re.compile(
    r"^(noqa\b|type:|fmt:|pragma\b|pyright:|mypy:|ruff:|isort:|pylint:|-\*-|nosec\b)"
)


def _comment_text(token: tokenize.TokenInfo) -> str | None:
    """Returns the prose of a comment token, or None when it is not prose."""
    text = token.string[1:]
    text = text[1:] if text.startswith(" ") else text
    if token.start[0] == 1 and text.startswith("!"):
        return None
    stripped = text.strip()
    if _PRAGMA.match(stripped) or BANNER.match(stripped):
        return None
    # A single word is a section label such as "# warnings", not a sentence.
    if len(stripped.split()) == 1:
        return None
    if IGNORE_MARKER in stripped:
        return None
    return text.rstrip()


def _comments(source: str) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    current: Paragraph = []
    previous: tokenize.TokenInfo | None = None
    lines = source.splitlines()
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        row, column = token.start
        full_line = lines[row - 1][:column].strip() == ""
        continues = (
            full_line
            and previous is not None
            and previous.start[0] == row - 1
            and previous.start[1] == column
            and bool(current)
        )
        text = _comment_text(token)
        if not continues or text is None or not text.strip():
            if current:
                paragraphs.append(current)
            current = []
        if text is not None and text.strip():
            current.append(ProseLine(row, text))
            if not full_line:
                paragraphs.append(current)
                current = []
        previous = token if full_line else None
    if current:
        paragraphs.append(current)
    return paragraphs


def _docstring_nodes(tree: ast.Module) -> list[ast.Constant]:
    nodes: list[ast.Constant] = []
    owners: list[ast.AST] = [tree]
    owners.extend(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
    )
    for owner in owners:
        body = getattr(owner, "body", [])
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            nodes.append(body[0].value)
    return nodes


def _docstring_paragraphs(node: ast.Constant) -> list[Paragraph]:
    """Splits one docstring into paragraphs, skipping code examples."""
    assert isinstance(node.value, str)
    return split_block(node.value, node.lineno)


def extract_paragraphs(source: str) -> list[Paragraph]:
    """Extracts every prose paragraph from Python source.

    Comment blocks are consecutive full-line comments at the same column.
    A trailing comment after code is a paragraph of its own.
    Docstrings of modules, classes, and functions are split on blank lines.

    Args:
        source: The contents of a Python file.

    Returns:
        The paragraphs in source order. Unparsable source yields no paragraphs.
    """
    try:
        tree = ast.parse(source)
        paragraphs = _comments(source)
    except (SyntaxError, tokenize.TokenError):
        return []
    for node in _docstring_nodes(tree):
        paragraphs.extend(_docstring_paragraphs(node))
    return sorted(paragraphs, key=lambda paragraph: paragraph[0].line)
