from pathlib import Path

from dev_standards.sync import BLOCK_END, BLOCK_START, TARGETS, Result, sync

PYTHON = ("python",)
LUA = ("lua",)

# The .editorconfig that dev-standards v0.4.0 and older wrote as a whole managed file.
LEGACY_EDITORCONFIG = """\
# Shared editor settings for every repository that uses dev-standards.
# This file is managed by dev-standards. Change it there, not here.

root = true

[*]
indent_style = space

[*.lua]
indent_style = tab
"""


def read(root: Path, name: str) -> str:
    return (root / name).read_text(encoding="utf-8")


def test_fresh_python_repository_gets_every_file(tmp_path: Path) -> None:
    results = sync(tmp_path, fix=True, languages=PYTHON)
    assert set(results.values()) == {Result.CHANGED}
    for target in TARGETS:
        assert (tmp_path / target.path).is_file()


def test_second_run_is_a_no_op(tmp_path: Path) -> None:
    sync(tmp_path, fix=True, languages=PYTHON)
    results = sync(tmp_path, fix=False, languages=PYTHON)
    assert set(results.values()) == {Result.OK}


def test_check_mode_reports_without_writing(tmp_path: Path) -> None:
    results = sync(tmp_path, fix=False, languages=PYTHON)
    assert set(results.values()) == {Result.OUTDATED}
    assert not (tmp_path / ".editorconfig").exists()


def test_a_python_repository_gets_only_the_python_parts(tmp_path: Path) -> None:
    sync(tmp_path, fix=True, languages=PYTHON)

    assert "__pycache__/" in read(tmp_path, ".gitignore")
    assert ".env\n" in read(tmp_path, ".gitignore")
    assert "[*.lua]" not in read(tmp_path, ".editorconfig")


def test_a_lua_repository_gets_only_the_lua_parts(tmp_path: Path) -> None:
    results = sync(tmp_path, fix=True, languages=LUA)

    # The ruff baseline belongs to Python alone, so a Lua repository needs no skip for it.
    assert results[".ruff-base.toml"] is Result.UNUSED
    assert not (tmp_path / ".ruff-base.toml").exists()
    assert "[*.lua]" in read(tmp_path, ".editorconfig")
    gitignore = read(tmp_path, ".gitignore")
    assert ".env\n" in gitignore
    assert "__pycache__/" not in gitignore
    assert sync(tmp_path, fix=False, languages=LUA)[".editorconfig"] is Result.OK


def test_a_repository_of_both_languages_gets_both_parts(tmp_path: Path) -> None:
    sync(tmp_path, fix=True, languages=("python", "lua"))

    assert "[*.lua]" in read(tmp_path, ".editorconfig")
    assert "__pycache__/" in read(tmp_path, ".gitignore")
    assert (tmp_path / ".ruff-base.toml").is_file()


def test_editorconfig_keeps_the_repositorys_own_sections(tmp_path: Path) -> None:
    sync(tmp_path, fix=True, languages=LUA)
    editorconfig = tmp_path / ".editorconfig"
    own = "\n[*.ps1]\n# PowerShell 5.1 needs a BOM.\ncharset = utf-8-bom\n"
    editorconfig.write_text(read(tmp_path, ".editorconfig") + own, encoding="utf-8")

    assert sync(tmp_path, fix=False, languages=LUA)[".editorconfig"] is Result.OK
    sync(tmp_path, fix=True, languages=("python", "lua"))
    assert read(tmp_path, ".editorconfig").endswith(own)


def test_a_whole_editorconfig_from_before_is_replaced_not_kept(tmp_path: Path) -> None:
    (tmp_path / ".editorconfig").write_text(LEGACY_EDITORCONFIG, encoding="utf-8")

    results = sync(tmp_path, fix=True, languages=PYTHON)

    content = read(tmp_path, ".editorconfig")
    assert results[".editorconfig"] is Result.CHANGED
    assert content.startswith(BLOCK_START)
    assert content.endswith(BLOCK_END + "\n")
    # Nothing of the old copy stays below the block, so its Lua section is gone too.
    assert content.count("root = true") == 1
    assert "[*.lua]" not in content


def test_editorconfig_without_markers_or_legacy_line_is_kept(tmp_path: Path) -> None:
    (tmp_path / ".editorconfig").write_text(
        "[*.md]\nindent_size = 2\n", encoding="utf-8"
    )

    sync(tmp_path, fix=True, languages=PYTHON)

    assert read(tmp_path, ".editorconfig").endswith(
        f"{BLOCK_END}\n\n[*.md]\nindent_size = 2\n"
    )


def test_block_preserves_repository_lines(tmp_path: Path) -> None:
    gitattributes = tmp_path / ".gitattributes"
    gitattributes.write_text(
        "*.ogg filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8"
    )
    sync(tmp_path, fix=True, languages=PYTHON)
    content = gitattributes.read_text(encoding="utf-8")
    assert content.startswith(BLOCK_START)
    assert content.endswith("*.ogg filter=lfs diff=lfs merge=lfs -text\n")
    assert BLOCK_END in content


def test_block_is_replaced_in_place(tmp_path: Path) -> None:
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(
        f"local-top/\n{BLOCK_START}\nstale-entry\n{BLOCK_END}\nlocal-bottom/\n",
        encoding="utf-8",
    )
    sync(tmp_path, fix=True, languages=PYTHON)
    content = gitignore.read_text(encoding="utf-8")
    assert "stale-entry" not in content
    assert content.startswith("local-top/\n" + BLOCK_START)
    assert content.endswith(BLOCK_END + "\nlocal-bottom/\n")


def test_whole_file_is_overwritten(tmp_path: Path) -> None:
    (tmp_path / ".ruff-base.toml").write_text("line-length = 120\n", encoding="utf-8")
    results = sync(tmp_path, fix=True, languages=PYTHON)
    assert results[".ruff-base.toml"] is Result.CHANGED
    assert "line-length = 88" in read(tmp_path, ".ruff-base.toml")


def test_skip_leaves_target_alone(tmp_path: Path) -> None:
    results = sync(tmp_path, fix=True, languages=PYTHON, skip=(".gitignore",))
    assert results[".gitignore"] is Result.SKIPPED
    assert not (tmp_path / ".gitignore").exists()


def test_crlf_working_tree_counts_as_up_to_date(tmp_path: Path) -> None:
    sync(tmp_path, fix=True, languages=PYTHON)
    editorconfig = tmp_path / ".editorconfig"
    crlf = editorconfig.read_text(encoding="utf-8").replace("\n", "\r\n")
    editorconfig.write_bytes(crlf.encode("utf-8"))
    assert sync(tmp_path, fix=False, languages=PYTHON)[".editorconfig"] is Result.OK
