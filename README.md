# discord-dev-standards

Shared conventions, pre-commit hooks, and CI for the Discord bot and API repositories.
Every rule lives here once, and each repository consumes it at a pinned version.
Changing a rule means changing it here, tagging a release, and bumping the tag in the other repositories.

## What this repository provides

| Piece | Purpose |
|---|---|
| `check-prose` hook | Enforces the prose rules on Python comments, Python docstrings, and Markdown. |
| `sync-files` hook | Keeps `.editorconfig`, `.ruff-base.toml`, and managed blocks in `.gitattributes` and `.gitignore` identical everywhere. |
| `dev-standards template-check` | Reports where a derived repository has drifted from the template it was created from. |
| `python-ci.yml` | A reusable GitHub Actions workflow that lints, tests, type-checks, and builds the Docker image. |

## Prose rules

These rules apply to comments, docstrings, Markdown, commit message bodies, and user-facing text.

* Write full, short sentences that end with a period.
* Break a line only after a period. Never wrap one sentence across two lines.
* Do not use semicolons in prose. Split the thought into two sentences instead.
* Use em dashes sparingly. Code comments and docstrings allow none, and a Markdown paragraph allows one.
* Headings, table cells, code, and command lines are not prose and are exempt.

The `check-prose` hook reports each violation with a code:

| Code | Meaning |
|---|---|
| P001 | A semicolon appears in prose. |
| P002 | A paragraph has more em dashes than allowed. |
| P003 | A sentence wraps onto the next line. |
| P004 | A sentence does not end with a period, question mark, exclamation mark, or colon. |

Code spans, URLs, and link targets are removed before checking, so `a; b` in backticks is fine.
Pragma comments such as `# noqa` or `# type: ignore` are never treated as prose.
Doctest examples, fenced code, literal blocks after `::`, and `Examples:` or `Usage:` sections in docstrings are skipped.

To exempt a single deliberate exception, add `prose: ignore` to the Python comment or docstring line.
In Markdown, put `<!-- prose: ignore -->` on the line before the paragraph.

## Python conventions

The baseline is PEP 8 as enforced by ruff, with these deliberate choices:

* Python 3.12 everywhere, matching the Docker images.
* Line length 88 for the formatter. The linter only rejects lines longer than 100 characters, because comments and docstrings are never wrapped mid-sentence.
* Double quotes, `X | None` instead of `Optional[X]`, and f-strings for formatting.
* Google-style docstrings on every public module, class, and function.
* Type annotations on every function signature, including private ones.
* `pathlib.Path` instead of `os.path`.

`.ruff-base.toml` encodes these rules.
Each repository's `ruff.toml` extends it and adds only repository-specific settings.
Add per-file exceptions under `[lint.extend-per-file-ignores]`.
A `[lint.per-file-ignores]` table replaces the baseline's table, which drops its exemption of tests from the docstring rules.

## Commit messages

Commits follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) with a scope where one fits.
The subject is imperative, lowercase, and has no trailing period.
The body follows the prose rules above, with one sentence per line.

## Using the hooks

Add this to a repository's `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/Lempki/discord-dev-standards
  rev: v0.1.3
  hooks:
    - id: sync-files
    - id: check-prose
```

Install the hooks once per clone with `uvx pre-commit install`.
Run them on demand with `uvx pre-commit run --all-files`.

Settings go in the repository's `pyproject.toml`:

```toml
[tool.dev-standards.prose]
exclude = ["tests/**"]        # Glob patterns that are never checked.
python-max-em-dashes = 0      # Per comment block or docstring paragraph.
markdown-max-em-dashes = 1    # Per Markdown paragraph or list item.

[tool.dev-standards.sync]
skip = [".gitignore"]         # Canonical files this repository opts out of.

[tool.dev-standards.template]
package = "media_api"         # Replaces {package} in template manifest paths.
ignore = ["cogs/help.py"]     # Manifest paths this repository deliberately diverges on.
```

## Checking template drift

The bot and API templates list their shared core files in `.template-manifest.toml`.
From a derived repository, compare it with its template:

```bash
uvx --from git+https://github.com/Lempki/discord-dev-standards@v0.1.3 dev-standards template-check --template ../discord-bot-template --diff
```

Pass `--apply` to overwrite drifted files with the template copy, then review the result with `git diff`.
The command exits with 1 while any file has drifted, so it also works as a CI gate.

## Using the reusable workflow

A repository's `.github/workflows/ci.yml` only needs to call the shared workflow:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  ci:
    uses: Lempki/discord-dev-standards/.github/workflows/python-ci.yml@v0.1.3
    with:
      mypy: true
      docker: true
      forward-python-version: "3.14"
```

| Input | Default | Effect |
|---|---|---|
| `python-version` | `3.12` | The Python version used by every job. |
| `forward-python-version` | Empty | Adds a job that runs the tests on this newer Python. It warns about an upgrade's breakage before the upgrade. |
| `mypy` | `false` | Adds a `typecheck` job that runs mypy on `mypy-target`. |
| `mypy-target` | `src` | The path mypy checks. |
| `docker` | `false` | Adds a `docker` job that builds the image without pushing it. |
| `lfs` | `false` | Checks out Git LFS files. Leave it off unless tests need real assets. |

## Releasing a new version

1. Change the rules, canonical files, or workflow here, with tests.
2. Bump `version` in `pyproject.toml` and tag the commit, for example `v0.2.0`.
3. In each repository, bump `rev` in `.pre-commit-config.yaml` and the `@v0.x.y` reference in `ci.yml`.
4. Run `uvx pre-commit run --all-files` so `sync-files` rolls out the new canonical files.

Dependabot bumps the workflow reference automatically.
