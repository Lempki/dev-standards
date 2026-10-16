from pathlib import Path

import pytest

from dev_standards.config import ConfigError, load_settings


def test_no_settings_file_gives_the_defaults(tmp_path: Path) -> None:
    settings = load_settings(tmp_path)

    assert settings.prose.exclude == ()
    assert settings.prose.lua_max_em_dashes == 0
    assert settings.sync.skip == ()


def test_reads_the_pyproject_table(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.dev-standards.prose]\nexclude = ["tests/**"]\n', encoding="utf-8"
    )

    assert load_settings(tmp_path).prose.exclude == ("tests/**",)


def test_reads_dev_standards_toml_in_a_repository_without_pyproject(
    tmp_path: Path,
) -> None:
    (tmp_path / "dev-standards.toml").write_text(
        '[prose]\nlua-max-em-dashes = 1\n\n[sync]\nskip = [".ruff-base.toml"]\n',
        encoding="utf-8",
    )

    settings = load_settings(tmp_path)

    assert settings.prose.lua_max_em_dashes == 1
    assert settings.sync.skip == (".ruff-base.toml",)


def test_reads_dev_standards_toml_beside_a_pyproject_without_the_table(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\n', encoding="utf-8"
    )
    (tmp_path / "dev-standards.toml").write_text(
        '[sync]\nskip = [".gitignore"]\n', encoding="utf-8"
    )

    assert load_settings(tmp_path).sync.skip == (".gitignore",)


def test_refuses_settings_in_both_files(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.dev-standards.sync]\nskip = [".gitignore"]\n', encoding="utf-8"
    )
    (tmp_path / "dev-standards.toml").write_text(
        '[sync]\nskip = [".gitignore"]\n', encoding="utf-8"
    )

    with pytest.raises(ConfigError, match="both"):
        load_settings(tmp_path)


def test_rejects_a_negative_em_dash_limit(tmp_path: Path) -> None:
    (tmp_path / "dev-standards.toml").write_text(
        "[prose]\nlua-max-em-dashes = -1\n", encoding="utf-8"
    )

    with pytest.raises(ConfigError, match="lua-max-em-dashes"):
        load_settings(tmp_path)
