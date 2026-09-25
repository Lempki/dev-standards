"""Prose rules shared by the Python and Markdown extractors.

An extractor turns a file into paragraphs of prose lines.
The rules below only ever see those paragraphs, never the original syntax.
"""

import re
from dataclasses import dataclass
from pathlib import Path

__all__ = ["EM_DASH", "Paragraph", "ProseLine", "Violation", "check_paragraph"]

EM_DASH = "—"

_TERMINALS = (".", "?", "!", ":")
_CLOSERS = ")]\"'*_”’»"
_CODE_SPAN = re.compile(r"(`+)(.+?)\1")
_URL = re.compile(r"<?https?://[^\s>)]+>?")
_LINK_TARGET = re.compile(r"\]\([^)]*\)")
_HTML_ENTITY = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);")


@dataclass(frozen=True)
class ProseLine:
    """One physical line of prose.

    Attributes:
        line: The 1-based line number in the source file.
        text: The prose with markup such as comment markers or list bullets removed.
    """

    line: int
    text: str


Paragraph = list[ProseLine]


@dataclass(frozen=True, order=True)
class Violation:
    """A single rule violation, ordered by location."""

    path: Path
    line: int
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.path.as_posix()}:{self.line}: {self.code} {self.message}"


def _without_code(text: str) -> str:
    """Removes code spans, URLs, link targets, and HTML entities from prose."""
    text = _CODE_SPAN.sub("", text)
    text = _LINK_TARGET.sub("]", text)
    text = _URL.sub("", text)
    return _HTML_ENTITY.sub("", text)


def _ends_sentence(text: str) -> bool:
    stripped = text.rstrip().rstrip(_CLOSERS).rstrip()
    if stripped.endswith(_TERMINALS):
        return True
    last_word = stripped.rsplit(maxsplit=1)[-1] if stripped else ""
    return bool(_URL.fullmatch(last_word))


def check_paragraph(
    path: Path, paragraph: Paragraph, max_em_dashes: int
) -> list[Violation]:
    """Applies every prose rule to one paragraph.

    Args:
        path: The file the paragraph came from, used in the report.
        paragraph: The prose lines of the paragraph, in order.
        max_em_dashes: How many em dashes the paragraph may contain.

    Returns:
        The violations found, in line order.
    """
    violations: list[Violation] = []
    dashes = 0
    for index, prose in enumerate(paragraph):
        plain = _without_code(prose.text)
        if ";" in plain:
            violations.append(
                Violation(
                    path,
                    prose.line,
                    "P001",
                    "Semicolon in prose. Split it into two sentences.",
                )
            )
        for _ in range(plain.count(EM_DASH)):
            dashes += 1
            if dashes == max_em_dashes + 1:
                violations.append(
                    Violation(
                        path,
                        prose.line,
                        "P002",
                        f"More than {max_em_dashes} em dash(es) in one paragraph.",
                    )
                )
        if _ends_sentence(prose.text):
            continue
        if index + 1 < len(paragraph):
            violations.append(
                Violation(
                    path,
                    prose.line,
                    "P003",
                    "Sentence wraps onto the next line. Break lines only after a period.",
                )
            )
        else:
            violations.append(
                Violation(
                    path, prose.line, "P004", "Sentence does not end with a period."
                )
            )
    return violations
