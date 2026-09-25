from pathlib import Path

from dev_standards.sync import BLOCK_END, BLOCK_START, TARGETS, Result, sync


def test_fresh_repository_gets_every_file(tmp_path: Path) -> None:
    results = sync(tmp_path, fix=True)
    assert set(results.values()) == {Result.CHANGED}
    for target in TARGETS:
        assert (tmp_path / target.path).is_file()


def test_second_run_is_a_no_op(tmp_path: Path) -> None:
    sync(tmp_path, fix=True)
    results = sync(tmp_path, fix=False)
    assert set(results.values()) == {Result.OK}


def test_check_mode_reports_without_writing(tmp_path: Path) -> None:
    results = sync(tmp_path, fix=False)
    assert set(results.values()) == {Result.OUTDATED}
    assert not (tmp_path / ".editorconfig").exists()


def test_block_preserves_repository_lines(tmp_path: Path) -> None:
    gitattributes = tmp_path / ".gitattributes"
    gitattributes.write_text(
        "*.ogg filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8"
    )
    sync(tmp_path, fix=True)
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
    sync(tmp_path, fix=True)
    content = gitignore.read_text(encoding="utf-8")
    assert "stale-entry" not in content
    assert content.startswith("local-top/\n" + BLOCK_START)
    assert content.endswith(BLOCK_END + "\nlocal-bottom/\n")


def test_whole_file_is_overwritten(tmp_path: Path) -> None:
    (tmp_path / ".editorconfig").write_text("root = false\n", encoding="utf-8")
    results = sync(tmp_path, fix=True)
    assert results[".editorconfig"] is Result.CHANGED
    assert "root = true" in (tmp_path / ".editorconfig").read_text(encoding="utf-8")


def test_skip_leaves_target_alone(tmp_path: Path) -> None:
    results = sync(tmp_path, fix=True, skip=(".gitignore",))
    assert results[".gitignore"] is Result.SKIPPED
    assert not (tmp_path / ".gitignore").exists()


def test_crlf_working_tree_counts_as_up_to_date(tmp_path: Path) -> None:
    sync(tmp_path, fix=True)
    editorconfig = tmp_path / ".editorconfig"
    crlf = editorconfig.read_text(encoding="utf-8").replace("\n", "\r\n")
    editorconfig.write_bytes(crlf.encode("utf-8"))
    assert sync(tmp_path, fix=False)[".editorconfig"] is Result.OK
