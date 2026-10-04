"""The template-check command.

A template repository lists its shared core files in .template-manifest.toml.
A derived repository is expected to carry identical copies of those files.
"""

import difflib
import tomllib
from dataclasses import dataclass
from enum import Enum
from fnmatch import fnmatchcase
from importlib.resources import files
from pathlib import Path, PurePosixPath

from .config import load_settings

__all__ = ["MANIFEST_NAME", "Drift", "FileState", "ManifestError", "check_template"]

MANIFEST_NAME = ".template-manifest.toml"
_PLACEHOLDER = "{package}"


class ManifestError(Exception):
    """Raised when a template manifest is missing or malformed."""


class FileState(Enum):
    """How a derived file compares to the template's copy."""

    IDENTICAL = "identical"
    DIFFERS = "differs"
    MISSING = "missing"
    IGNORED = "ignored"


@dataclass(frozen=True)
class Drift:
    """The comparison result for one manifest entry.

    Attributes:
        manifest_path: The path as written in the manifest.
        template_file: The resolved file in the template repository.
        derived_file: The resolved file in the derived repository.
        state: How the two copies compare.
    """

    manifest_path: str
    template_file: Path
    derived_file: Path
    state: FileState

    def diff(self) -> str:
        """Returns a unified diff from the template copy to the derived copy."""
        if self.state is not FileState.DIFFERS:
            return ""
        template_lines = _read(self.template_file).splitlines(keepends=True)
        derived_lines = _read(self.derived_file).splitlines(keepends=True)
        return "".join(
            difflib.unified_diff(
                template_lines,
                derived_lines,
                fromfile=f"template/{self.manifest_path}",
                tofile=f"derived/{self.manifest_path}",
            )
        )


def _read(path: Path) -> str:
    # Universal newline mode reads CRLF as LF, so a Windows working tree never reads as drift.
    return path.read_text(encoding="utf-8")


def _line_ending(manifest_path: str) -> str:
    """Returns the line ending that Git checks a file out with.

    The canonical .gitattributes block decides it, so an applied file looks like a fresh checkout.
    cmd.exe can misread a batch file with LF line endings, which makes CRLF matter there.
    As in Git, the last matching line wins.
    A pattern without a slash matches the file name in any folder.

    Args:
        manifest_path: The path as written in the manifest, relative to the repository root.

    Returns:
        CRLF for a path the block marks eol=crlf, otherwise LF.
    """
    block = files("dev_standards").joinpath("canonical", "gitattributes.block")
    ending = "\n"
    for line in block.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if not fields or fields[0].startswith("#"):
            continue
        pattern, attributes = fields[0], fields[1:]
        if "/" in pattern:
            matches = fnmatchcase(manifest_path, pattern.lstrip("/"))
        else:
            matches = fnmatchcase(PurePosixPath(manifest_path).name, pattern)
        if matches and "eol=crlf" in attributes:
            ending = "\r\n"
        elif matches and "eol=lf" in attributes:
            ending = "\n"
    return ending


def _manifest_paths(template_root: Path) -> list[str]:
    manifest = template_root / MANIFEST_NAME
    if not manifest.is_file():
        raise ManifestError(f"{manifest} does not exist.")
    with manifest.open("rb") as file:
        data = tomllib.load(file)
    error = ManifestError(f"{manifest} must list [[file]] entries with a 'path'.")
    paths: list[str] = []
    for entry in data.get("file", []):
        path = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(path, str):
            raise error
        paths.append(path)
    if not paths:
        raise error
    return paths


def _resolve(manifest_path: str, package: str | None, root: Path) -> Path:
    if _PLACEHOLDER not in manifest_path:
        return root / manifest_path
    if package is None:
        raise ManifestError(
            f"{root.name} needs [tool.dev-standards.template] package to resolve "
            f"'{manifest_path}'."
        )
    return root / manifest_path.replace(_PLACEHOLDER, package)


def check_template(
    template_root: Path, derived_root: Path, *, apply: bool
) -> list[Drift]:
    """Compares a derived repository's core files with its template.

    Args:
        template_root: The template repository root, which holds the manifest.
        derived_root: The derived repository root.
        apply: Whether to overwrite differing or missing derived files with the template copy.
            A written file gets the line ending that the canonical .gitattributes block gives it.

    Returns:
        One result per manifest entry, in manifest order.
        Applied files are reported with the state they had before the copy.

    Raises:
        ManifestError: If the manifest is missing, malformed, or needs an unset package name.
    """
    template_settings = load_settings(template_root).template
    derived_settings = load_settings(derived_root).template
    results: list[Drift] = []
    for manifest_path in _manifest_paths(template_root):
        template_file = _resolve(
            manifest_path, template_settings.package, template_root
        )
        derived_file = _resolve(manifest_path, derived_settings.package, derived_root)
        if manifest_path in derived_settings.ignore:
            state = FileState.IGNORED
        elif not derived_file.is_file():
            state = FileState.MISSING
        elif _read(template_file) == _read(derived_file):
            state = FileState.IDENTICAL
        else:
            state = FileState.DIFFERS
        results.append(Drift(manifest_path, template_file, derived_file, state))
        if apply and state in (FileState.DIFFERS, FileState.MISSING):
            derived_file.parent.mkdir(parents=True, exist_ok=True)
            derived_file.write_text(
                _read(template_file),
                encoding="utf-8",
                newline=_line_ending(manifest_path),
            )
    return results
