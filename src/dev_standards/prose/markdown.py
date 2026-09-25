"""Extracts prose paragraphs from Markdown.

Headings, tables, code, HTML, and link-only lines carry no sentences, so they are skipped.
"""

import re

from .rules import Paragraph, ProseLine

__all__ = ["IGNORE_COMMENT", "extract_paragraphs"]

IGNORE_COMMENT = "<!-- prose: ignore -->"

_FENCE = re.compile(r"^(`{3,}|~{3,})")
_HEADING = re.compile(r"^#{1,6}(\s|$)")
_RULE = re.compile(r"^([-*_])(\s*\1){2,}$")
_LINK_DEFINITION = re.compile(r"^\[[^\]]+\]:\s")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")
_LIST_ITEM = re.compile(r"^([-*+]|\d+[.)])\s+(\[[ xX]\]\s+)?")
_QUOTE = re.compile(r"^(>\s?)+")


def _is_structural(text: str) -> bool:
    return bool(
        _HEADING.match(text)
        or text.startswith(("|", "<"))
        or _RULE.match(text)
        or _LINK_DEFINITION.match(text)
        or not _LINK.sub("", _IMAGE.sub("", text)).strip()
    )


def extract_paragraphs(source: str) -> list[Paragraph]:
    """Extracts every prose paragraph from Markdown source.

    Each list item starts a new paragraph, so every bullet must be a full sentence.
    A paragraph preceded by an ignore comment is skipped.

    Args:
        source: The contents of a Markdown file.

    Returns:
        The paragraphs in source order.
    """
    paragraphs: list[Paragraph] = []
    current: Paragraph = []
    fence: str | None = None
    in_comment = False
    in_front_matter = False
    # The ignore comment skips one paragraph, so skipping ends at the next boundary.
    skipping = False
    skipped_any = False

    def close() -> None:
        nonlocal current, skipping, skipped_any
        if current:
            paragraphs.append(current)
        current = []
        if skipped_any:
            skipping = skipped_any = False

    for number, raw in enumerate(source.splitlines(), start=1):
        text = raw.strip()
        if number == 1 and text == "---":
            in_front_matter = True
            continue
        if in_front_matter:
            in_front_matter = text != "---"
            continue
        fence_match = _FENCE.match(text)
        if fence is not None:
            if fence_match and text.startswith(fence):
                fence = None
            continue
        if fence_match:
            close()
            fence = fence_match.group(1)[0] * 3
            continue
        if in_comment:
            in_comment = "-->" not in text
            continue
        if text == IGNORE_COMMENT:
            close()
            skipping = True
            continue
        if text.startswith("<!--"):
            close()
            in_comment = "-->" not in text
            continue
        text = _QUOTE.sub("", text).strip()
        if not text or _is_structural(text):
            close()
            continue
        item = _LIST_ITEM.match(text)
        if item:
            close()
            text = text[item.end() :]
        if skipping:
            skipped_any = True
            continue
        current.append(ProseLine(number, text))
    close()
    return paragraphs
