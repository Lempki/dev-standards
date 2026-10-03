"""Command-line entry point for the dev-standards hooks and tools.

Usage:
    dev-standards check-prose FILE...
    dev-standards sync-files [--fix]
    dev-standards template-check --template PATH [--derived PATH] [--diff] [--apply]
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .config import ConfigError, load_settings
from .prose import check_paths
from .sync import Result, sync
from .template import FileState, ManifestError, check_template

__all__ = ["main"]


def _check_prose(args: argparse.Namespace) -> int:
    root = Path.cwd()
    config = load_settings(root).prose
    violations = check_paths([Path(p) for p in args.files], root, config)
    for violation in violations:
        print(violation)
    if violations:
        print(f"\n{len(violations)} prose violation(s). See the dev-standards README.")
        return 1
    # pre-commit hides the output of a passing hook, so this line shows only on a direct run.
    print(f"Checked {len(args.files)} file(s). No prose violations.")
    return 0


def _sync_files(args: argparse.Namespace) -> int:
    root = Path.cwd()
    skip = load_settings(root).sync.skip
    results = sync(root, fix=args.fix, skip=skip)
    failed = False
    for path, result in results.items():
        if result in (Result.CHANGED, Result.OUTDATED):
            print(f"{path}: {result.value}.")
            failed = True
    return 1 if failed else 0


def _template_check(args: argparse.Namespace) -> int:
    results = check_template(Path(args.template), Path(args.derived), apply=args.apply)
    drifted = False
    for drift in results:
        print(f"{drift.state.value:>9}  {drift.manifest_path}")
        if drift.state in (FileState.DIFFERS, FileState.MISSING):
            drifted = True
            if args.diff:
                print(drift.diff())
    if drifted and args.apply:
        print(
            "\nDrifted files were overwritten with the template copy. Review them with git diff."
        )
        return 0
    return 1 if drifted else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dev-standards", description=__doc__.splitlines()[0]
    )
    commands = parser.add_subparsers(dest="command", required=True)

    prose = commands.add_parser(
        "check-prose", help="Check comments, docstrings, and Markdown."
    )
    prose.add_argument("files", nargs="*", help="Files to check.")
    prose.set_defaults(handler=_check_prose)

    files = commands.add_parser(
        "sync-files", help="Check or update canonical config files."
    )
    files.add_argument("--fix", action="store_true", help="Write out-of-date files.")
    files.set_defaults(handler=_sync_files)

    template = commands.add_parser(
        "template-check", help="Report drift from a template."
    )
    template.add_argument(
        "--template", required=True, help="Path to the template repository."
    )
    template.add_argument(
        "--derived", default=".", help="Path to the derived repository."
    )
    template.add_argument(
        "--diff", action="store_true", help="Show a diff for drifted files."
    )
    template.add_argument(
        "--apply", action="store_true", help="Copy template files over drift."
    )
    template.set_defaults(handler=_template_check)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Runs one dev-standards command.

    Args:
        argv: The arguments without the program name. Defaults to sys.argv.

    Returns:
        The process exit code. Zero means no violations or drift.
    """
    args = _parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except (ConfigError, ManifestError) as error:
        print(f"dev-standards: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
