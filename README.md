# dev-standards

Shared conventions, pre-commit hooks, and CI that keep a family of repositories consistent.
Every rule lives here once, and each repository consumes it at a pinned version.
Changing a rule means changing it here, tagging a release, and bumping the tag in the other repositories.

## What this repository provides

| Piece | Purpose |
|---|---|
| `check-prose` hook | Enforces the prose rules on Python comments, Python docstrings, and Markdown. |
| `sync-files` hook | Keeps `.editorconfig`, `.ruff-base.toml`, and managed blocks in `.gitattributes` and `.gitignore` identical everywhere. |
| `dev-standards template-check` | Reports where a derived repository has drifted from the template it was created from. |
| `python-ci.yml` | A reusable GitHub Actions workflow that lints, tests, type-checks, and builds the Docker image. |

## Language support

The engineering guidelines, the prose rules, the commit conventions, and the template drift check apply to any language.
The tooling that enforces them supports Python today.
`check-prose` reads Python comments, Python docstrings, and Markdown, while `.ruff-base.toml`, `python-ci.yml`, and the canonical `.gitignore` block are written for Python.
A new language adds its own pieces next to these, such as a comment reader in `src/dev_standards/prose/` and its own reusable workflow.

## Engineering guidelines

These guidelines apply to every change, whoever or whatever writes it.
The Python conventions below translate them into Python specifics.

### Scope and style

* Understand the surrounding code before changing it, and fit into the existing architecture instead of introducing a new one.
* Keep each change as small as the problem allows. Do not rename, reorganize, or restyle unrelated code in the same change.
* Prefer the plain solution that states its intent. Clever one-liners, deep nesting, and abstractions without a concrete reason make code harder to read later.
* A few extra lines are better than a dense expression that the reader has to unpack, but do not pad code just to make it longer.
* When the existing design makes a change unreasonably hard, say so before widening the scope.

### Comments

* A comment explains why the code is the way it is, not what it visibly does.
* Good reasons for a comment are a business rule, a constraint, a workaround for external behavior, or an implementation that looks wrong but is intentional.
* Comments never mention chats, prompts, AI assistants, or how the code was produced.
* When a better name would make a comment unnecessary, change the name instead.

### Errors and logging

* Catch an exception only when there is something meaningful to do with it, and keep the original error as the cause.
* Validate external input at trust boundaries, such as requests, files, and environment variables. Inside the code, trust the types.
* Log what helps diagnose a problem, with enough context to understand the event on its own. Log an error once, at the layer that knows the most about it.
* Never log, print, or echo secrets, tokens, or credentials.

### Dependencies

* Prefer the standard library or an existing dependency when it does the job clearly.
* Before adding a package, check its license, its maintenance status, and what it pulls in. A GPL dependency cannot ship in an MIT project, and an unmaintained one becomes a future migration.

### Testing and validation

* Test behavior and contracts, not implementation details.
* A bug fix comes with a regression test when practical.
* Never claim that tests, linters, or builds passed unless they actually ran. Say what was not verified.

### Ambiguity

* When an ambiguity changes the outcome, ask.
* Otherwise choose the least surprising interpretation and state the assumption.

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
* Specific exceptions only. Keep the cause with `raise NewError(...) from err`, and never silence `Exception`.
* Keyword-only flags and options, declared after `*`, so a call reads `play(track, loop=True)` instead of `play(track, True)`.
* mypy's `None` analysis is part of the design. Do not silence it with `# type: ignore` or `cast()` unless an invariant guarantees the type, and return an empty collection instead of `None` when "nothing" is the answer.
* No blocking I/O or heavy computation directly in async code, because it stalls the event loop. Run it with `asyncio.to_thread`.
* A regular expression that is not trivial gets a name as a module constant and tests for its edge cases. Use string methods when they are clearer.

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
- repo: https://github.com/Lempki/dev-standards
  rev: v0.2.0
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
uvx --from git+https://github.com/Lempki/dev-standards@v0.2.0 dev-standards template-check --template ../discord-bot-template --diff
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
    uses: Lempki/dev-standards/.github/workflows/python-ci.yml@v0.2.0
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

Dependabot bumps the workflow reference and the hook revision automatically, in separate pull requests.

## License

This project is licensed under the [MIT License](LICENSE).
You may use, change, and share it, as long as every copy keeps the copyright notice and the license text.
