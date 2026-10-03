from pathlib import Path

import pytest

from dev_standards.config import ProseConfig
from dev_standards.prose import check_file, check_paths

CONFIG = ProseConfig()


def codes(
    name: str, source: str, config: ProseConfig = CONFIG
) -> list[tuple[int, str]]:
    return [(v.line, v.code) for v in check_file(Path(name), source, config)]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("# A full sentence.\n", []),
        ("# Two sentences. Both end properly.\n", []),
        ("# Missing the period\n", [(1, "P004")]),
        ("# First half of a sentence\n# second half.\n", [(1, "P003")]),
        ("# One sentence.\n# Another sentence.\n", []),
        ("# This part; that part.\n", [(1, "P001")]),
        ("# Uses a dash — here.\n", [(1, "P002")]),
        ("# Code like `a; b` is ignored.\n", []),
        ("# See https://example.com/a;b\n", []),
        ("# Heading-style colon:\n# Then a sentence.\n", []),
        ("x = 1  # trailing comment\n", [(1, "P004")]),
        ("x = 1  # Trailing sentence.\n", []),
        ("x = 1  # noqa: E501\n", []),
        ("x = 1  # type: ignore[misc]\n", []),
        ("#!/usr/bin/env python\n", []),
        ("# --- Settings ---\n", []),
        ("# -------------\n", []),
        ("# fmt: off\n", []),
        ("# set_channel\n", []),
        ("# ---\n# warnings\n# ---\n", []),
        ("# Two words\n", [(1, "P004")]),
        ("# Deliberate fragment prose: ignore\n", []),
        ("# Ends in a quote (like this).\n", []),
    ],
)
def test_python_comments(source: str, expected: list[tuple[int, str]]) -> None:
    assert codes("m.py", source) == expected


def test_comment_blocks_split_on_column_change() -> None:
    source = (
        "def f() -> None:\n    # Indented sentence.\n    pass\n# Top level sentence.\n"
    )
    assert codes("m.py", source) == []


def test_blank_comment_line_splits_paragraphs() -> None:
    source = "# First paragraph\n#\n# Second paragraph.\n"
    assert codes("m.py", source) == [(1, "P004")]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('"""One line docstring."""\n', []),
        ('"""One line docstring"""\n', [(1, "P004")]),
        (
            'def f() -> None:\n    """Wrapped over\n    two lines.\n    """\n',
            [(2, "P003")],
        ),
        (
            "def f(a: int) -> int:\n"
            '    """Doubles a number.\n'
            "\n"
            "    Args:\n"
            "        a: The number.\n"
            "\n"
            "    Returns:\n"
            "        Twice the number.\n"
            '    """\n',
            [],
        ),
        ('"""Summary.\n\n>>> f(1)\n2\n"""\n', []),
        ('"""Summary.\n\n>>> f(1)\n2\n\nAfter the example\n"""\n', [(6, "P004")]),
        ('"""Summary.\n\nExample:\n    run_this --now\n    and_this\n"""\n', []),
        ('"""Summary.\n\nUsage:\n    tool check FILE...\n"""\n', []),
        ('"""Summary.\n\nA literal block::\n\n    raw text\n"""\n', []),
        ('"""Summary.\n\n```\ncode here\n```\n"""\n', []),
        ('"""Uses an em dash — badly."""\n', [(1, "P002")]),
    ],
)
def test_python_docstrings(source: str, expected: list[tuple[int, str]]) -> None:
    assert codes("m.py", source) == expected


def test_python_em_dash_limit_is_configurable() -> None:
    config = ProseConfig(python_max_em_dashes=1)
    assert codes("m.py", "# One — dash is fine.\n", config) == []


def test_unparsable_python_is_skipped() -> None:
    assert codes("m.py", "def broken(:\n    # no period\n") == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("A full sentence.\n", []),
        ("Wrapped across\ntwo lines.\n", [(1, "P003")]),
        ("No period\n", [(1, "P004")]),
        ("# Heading without period\n", []),
        ("| a | b; c | — |\n|---|---|---|\n", []),
        ("```\nnot; prose\n```\n", []),
        ("   ```bash\n   run --this\n   ```\n", []),
        ("* First item.\n* Second item\n", [(2, "P004")]),
        ("1. Numbered item.\n2. Another.\n", []),
        ("- [ ] Task item.\n", []),
        ("> Quoted sentence.\n", []),
        ("[![badge](https://x/y.svg)](https://x)\n", []),
        ('<p align="center">\n', []),
        ("---\ntitle: x\n---\nBody sentence.\n", []),
        ("One — dash is allowed.\n", []),
        ("Two — dashes — are not.\n", [(1, "P002")]),
        ("Use `a; b` in code.\n", []),
        ("See [the docs](https://x.y/a;b).\n", []),
        ("<!-- prose: ignore -->\nFragment here\n\nChecked again\n", [(4, "P004")]),
        ("<!--\nA multi-line comment\n-->\nSentence.\n", []),
        ("Intro line:\n\n* Item one.\n", []),
    ],
)
def test_markdown(source: str, expected: list[tuple[int, str]]) -> None:
    assert codes("README.md", source) == expected


def test_other_file_types_are_ignored() -> None:
    assert codes("config.toml", "# no period\n") == []


def test_check_paths_honors_excludes(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text("# no period\n", encoding="utf-8")
    (tmp_path / "m.py").write_text("# no period\n", encoding="utf-8")
    config = ProseConfig(exclude=("tests/**",))
    paths = [tmp_path / "tests" / "t.py", tmp_path / "m.py"]
    violations = check_paths(paths, tmp_path, config)
    assert [v.path.name for v in violations] == ["m.py"]


def test_cli_reports_a_clean_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from dev_standards.cli import main

    (tmp_path / "clean.md").write_text("One sentence.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert main(["check-prose", "clean.md"]) == 0
    assert capsys.readouterr().out == "Checked 1 file(s). No prose violations.\n"


def test_cli_reports_violations_with_a_failing_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from dev_standards.cli import main

    (tmp_path / "bad.md").write_text("One; two.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert main(["check-prose", "bad.md"]) == 1
    assert "1 prose violation(s)." in capsys.readouterr().out
