from pathlib import Path

import pytest

from dev_standards.cli import main
from dev_standards.template import FileState, ManifestError, check_template


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repos(tmp_path: Path) -> tuple[Path, Path]:
    template = tmp_path / "template"
    derived = tmp_path / "derived"
    write(
        template / ".template-manifest.toml",
        '[[file]]\npath = "utils/db.py"\n\n[[file]]\npath = "src/{package}/auth.py"\n',
    )
    write(
        template / "pyproject.toml",
        '[tool.dev-standards.template]\npackage = "api_template"\n',
    )
    write(template / "utils/db.py", "DB = 1\n")
    write(template / "src/api_template/auth.py", "AUTH = 1\n")
    write(
        derived / "pyproject.toml",
        '[tool.dev-standards.template]\npackage = "media_api"\n',
    )
    write(derived / "utils/db.py", "DB = 1\n")
    write(derived / "src/media_api/auth.py", "AUTH = 2\n")
    return template, derived


def states(results: list) -> dict[str, FileState]:
    return {r.manifest_path: r.state for r in results}


def test_reports_identical_and_differing(repos: tuple[Path, Path]) -> None:
    template, derived = repos
    assert states(check_template(template, derived, apply=False)) == {
        "utils/db.py": FileState.IDENTICAL,
        "src/{package}/auth.py": FileState.DIFFERS,
    }


def test_diff_shows_both_sides(repos: tuple[Path, Path]) -> None:
    template, derived = repos
    drift = check_template(template, derived, apply=False)[1]
    assert "-AUTH = 1" in drift.diff()
    assert "+AUTH = 2" in drift.diff()


def test_missing_file_is_reported_and_applied(repos: tuple[Path, Path]) -> None:
    template, derived = repos
    (derived / "utils/db.py").unlink()
    assert states(check_template(template, derived, apply=True))["utils/db.py"] is (
        FileState.MISSING
    )
    assert (derived / "utils/db.py").read_text(encoding="utf-8") == "DB = 1\n"
    assert set(states(check_template(template, derived, apply=False)).values()) == {
        FileState.IDENTICAL
    }


def test_ignored_paths_are_not_drift(repos: tuple[Path, Path]) -> None:
    template, derived = repos
    write(
        derived / "pyproject.toml",
        '[tool.dev-standards.template]\npackage = "media_api"\n'
        'ignore = ["src/{package}/auth.py"]\n',
    )
    result = states(check_template(template, derived, apply=False))
    assert result["src/{package}/auth.py"] is FileState.IGNORED


def test_crlf_copy_is_identical(repos: tuple[Path, Path]) -> None:
    template, derived = repos
    (derived / "utils/db.py").write_bytes(b"DB = 1\r\n")
    assert states(check_template(template, derived, apply=False))["utils/db.py"] is (
        FileState.IDENTICAL
    )


def test_missing_package_setting_raises(repos: tuple[Path, Path]) -> None:
    template, derived = repos
    (derived / "pyproject.toml").unlink()
    with pytest.raises(ManifestError, match="package"):
        check_template(template, derived, apply=False)


def test_missing_manifest_raises(tmp_path: Path) -> None:
    with pytest.raises(ManifestError):
        check_template(tmp_path, tmp_path, apply=False)


def test_cli_exit_codes(repos: tuple[Path, Path]) -> None:
    template, derived = repos
    assert (
        main(["template-check", "--template", str(template), "--derived", str(derived)])
        == 1
    )
    write(derived / "src/media_api/auth.py", "AUTH = 1\n")
    assert (
        main(["template-check", "--template", str(template), "--derived", str(derived)])
        == 0
    )
