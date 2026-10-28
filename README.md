# dev-standards

Shared conventions, pre-commit hooks, and CI that keep a family of repositories consistent.
Every rule lives here once, and each repository consumes it at a pinned version.
Changing a rule means changing it here, tagging a release, and bumping the tag in the other repositories.

## What this repository provides

| Piece | Purpose |
|---|---|
| `check-prose` hook | Enforces the prose rules on Python comments, Python docstrings, Lua comments, and Markdown. |
| `sync-files` hook | Keeps managed blocks in `.editorconfig`, `.gitattributes`, and `.gitignore`, and the whole `.ruff-base.toml`, identical in every repository of the same languages. |
| `dev-standards template-check` | Reports where a derived repository has drifted from the template it was created from. |
| `python-ci.yml` | A reusable GitHub Actions workflow that lints, tests, type-checks, and builds the Docker image. |
| `lua-ci.yml` | A reusable GitHub Actions workflow that runs the hooks, luacheck, and the tests under LuaJIT. |
| `docker-publish.yml` | A reusable GitHub Actions workflow that publishes a release's Docker image to the GitHub Container Registry. |

## Language support

The engineering guidelines, the prose rules, the commit conventions, and the template drift check apply to any language.
The tooling that enforces them supports Python and Lua.

| Language | Prose | Formatting and linting | Reusable workflow |
|---|---|---|---|
| Python | Comments and docstrings | `.ruff-base.toml` | `python-ci.yml` |
| Lua | Line comments and block comments | The canonical `.editorconfig` and each repository's `.luacheckrc` | `lua-ci.yml` |

`check-prose` also reads Markdown in every repository.
`sync-files` builds each shared file from a part that every repository gets and a part per language, and a repository gets only the parts of its languages.
A Python repository therefore gets `.ruff-base.toml` and the Python entries of `.gitignore`, and a Lua repository gets the tab rule for `.lua` files instead.

A repository's languages come from `languages` in its settings.
Without that setting, a marker file at the repository root tells them: `pyproject.toml` for Python and `.luacheckrc` for Lua.
A repository with neither must declare its languages, and a repository without code declares `languages = []`.

A new language adds its own pieces next to these: a comment reader in `src/dev_standards/prose/`, its canonical parts and marker file in `sync.py` and `config.py`, and its own reusable workflow.

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

In Lua, `-- luacheck:` options and annotations such as `---@param` are not prose either.
A line between two rule lines, such as `-- Public API` between `-- ####` lines, is a section heading.
Lua block comments are split on blank lines, like docstrings, and strings never count as comments.

To exempt a single deliberate exception, add `prose: ignore` to the Python comment or docstring line, or to the Lua comment line.
To skip a whole Lua block comment, such as commented-out code, put `prose: ignore` on its opening line.
In Markdown, put `<!-- prose: ignore -->` on the line before the paragraph.

## Python conventions

The baseline is PEP 8 as enforced by ruff, with these deliberate choices:

* Python 3.14 everywhere, matching the Docker images. Files under `scripts/` stay compatible with Python 3.12, because they run on the host's own Python.
* Line length 88 for the formatter. The linter only rejects lines longer than 100 characters, because comments and docstrings are never wrapped mid-sentence.
* Double quotes, `X | None` instead of `Optional[X]`, and f-strings for formatting.
* Google-style docstrings on every public module, class, and function.
* Type annotations on every function signature, including private ones.
* `pathlib.Path` instead of `os.path`.
* Specific exceptions only. Keep the cause with `raise NewError(...) from err`, and never silence `Exception`.
* Keyword-only flags and options, declared after `*`, so a call reads `save(path, overwrite=True)` instead of `save(path, True)`.
* mypy's `None` analysis is part of the design. Do not silence it with `# type: ignore` or `cast()` unless an invariant guarantees the type, and return an empty collection instead of `None` when "nothing" is the answer.
* No blocking I/O or heavy computation directly in async code, because it stalls the event loop. Run it with `asyncio.to_thread`.
* A regular expression that is not trivial gets a name as a module constant and tests for its edge cases. Use string methods when they are clearer.

`.ruff-base.toml` encodes these rules.
Each repository's `ruff.toml` extends it and adds only repository-specific settings.
Add per-file exceptions under `[lint.extend-per-file-ignores]`.
A `[lint.per-file-ignores]` table replaces the baseline's table, which drops its exemption of tests from the docstring rules.

## Lua conventions

The baseline is LuaJIT 2.1, the Lua that many host applications such as game engines embed, checked by luacheck, with these deliberate choices:

* Indent with tabs, as the canonical `.editorconfig` sets, so code that extends a host matches the host's own Lua.
* `std = "luajit"` in `.luacheckrc`, with the host's globals listed as `read_globals`, so a typo in a global name fails the check.
* Every variable and function is `local`, and each module returns one table.
* Code that runs in a host's shared Lua state, such as a game mod or a plugin, prefixes every name it adds there, including ffi declarations, so it cannot collide with other code in that state.
* Specs run under plain LuaJIT with a small runner and fakes for the host, so they need no third-party packages.
* A setting that a user can change is read where it is used, so a change applies without a restart.

## Commit messages

Commits follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) with a scope where one fits.
The subject is imperative, lowercase, and has no trailing period.
The body follows the prose rules above, with one sentence per line.
Mention issues as "Part of #N", never "Closes #N", because a push to main would close them before the release ships. Shipped issues are closed by hand at release time.

## Using the hooks

Add this to a repository's `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/Lempki/dev-standards
  rev: v0.6.1
  hooks:
    - id: sync-files
    - id: check-prose
```

Install the hooks once per clone with `uvx pre-commit install`.
Run them on demand with `uvx pre-commit run --all-files`.

Settings go in the `[tool.dev-standards]` table of the repository's `pyproject.toml`.
A repository without one, such as a Lua repository, puts the same settings in a `dev-standards.toml` at its root, without the `tool.dev-standards.` prefix.
Settings in both files are an error.

```toml
[tool.dev-standards]
languages = ["python"]       # Only needed when no marker file tells them. See Language support.

[tool.dev-standards.prose]
exclude = ["tests/**"]        # Glob patterns that are never checked.
python-max-em-dashes = 0      # Per comment block or docstring paragraph.
lua-max-em-dashes = 0         # Per Lua comment block or block comment paragraph.
markdown-max-em-dashes = 1    # Per Markdown paragraph or list item.

[tool.dev-standards.sync]
skip = [".gitattributes"]     # Shared files this repository opts out of.

[tool.dev-standards.template]
package = "my_service"        # Replaces {package} in template manifest paths.
ignore = ["Dockerfile"]       # Manifest paths this repository deliberately diverges on.
```

The same settings for a Lua repository, in `dev-standards.toml`:

```toml
languages = ["lua"]           # Only needed without a .luacheckrc.

[prose]
exclude = ["vendor/**"]
```

The managed block in `.gitignore`, `.gitattributes`, and `.editorconfig` belongs to dev-standards, and the lines outside it belong to the repository.
A repository adds its own entries below the block, such as an `.editorconfig` section for its PowerShell scripts:

```ini
# <<< dev-standards managed block.

[*.ps1]
# Windows PowerShell 5.1 reads UTF-8 without a BOM as ANSI.
charset = utf-8-bom
```

An `.editorconfig` section of the repository's own goes below the block, because the block starts with `root = true`, which must come before every section.
An `.editorconfig` that an older version wrote as a whole managed file is replaced by the block on the first run.

## Checking template drift

A template repository lists the core files that every repository made from it shares in `.template-manifest.toml`.
From a derived repository, compare it with its template:

```bash
uvx --from git+https://github.com/Lempki/dev-standards@v0.6.1 dev-standards template-check --template ../my-template --diff
```

Pass `--apply` to overwrite drifted files with the template copy, then review the result with `git diff`.
Each written file gets the line ending that the canonical `.gitattributes` block gives it, so a `.bat` file keeps CRLF.
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
    uses: Lempki/dev-standards/.github/workflows/python-ci.yml@v0.6.1
    with:
      mypy: true
      docker: true
      smoke-test: .github/smoke-test.sh
      forward-python-version: "3.15"
```

| Input | Default | Effect |
|---|---|---|
| `python-version` | `3.14` | The Python version used by every job. |
| `forward-python-version` | Empty | Adds a job that runs the tests on this newer Python. It warns about an upgrade's breakage before the upgrade, and its failure does not fail the run. |
| `mypy` | `false` | Adds a `typecheck` job that runs mypy on `mypy-target`. |
| `mypy-target` | `src` | The path mypy checks. |
| `docker` | `false` | Adds a `docker` job that builds the image without pushing it. |
| `smoke-test` | Empty | A script in the repository, such as `.github/smoke-test.sh`, that the `docker` job runs with the built image's name. It starts the image and fails when the program inside cannot start, which a build alone never shows. |
| `lfs` | `false` | Checks out Git LFS files. Leave it off unless tests need real assets. |

A Lua repository calls `lua-ci.yml` instead:

```yaml
jobs:
  ci:
    uses: Lempki/dev-standards/.github/workflows/lua-ci.yml@v0.6.1
    with:
      test-command: luajit tests/run.lua
```

| Input | Default | Effect |
|---|---|---|
| `test-command` | `luajit tests/run.lua` | The command that runs the tests under LuaJIT 2.1. Empty skips the `test` job. |
| `luacheck-paths` | `.` | The paths luacheck checks, with the repository's `.luacheckrc`. |
| `lfs` | `false` | Checks out Git LFS files. |

The `lint` job runs the repository's pre-commit hooks, as in `python-ci.yml`.

## Publishing Docker images

A repository's `.github/workflows/release.yml` publishes the image of every version tag:

```yaml
name: Release

on:
  push:
    tags: ["v*"]

jobs:
  image:
    uses: Lempki/dev-standards/.github/workflows/docker-publish.yml@v0.6.1
    permissions:
      contents: read
      packages: write
```

The image is named after the repository, such as `ghcr.io/<owner>/<repository>`.
Tag `v1.2.0` publishes the tags `1.2.0`, `1.2`, and `latest`.
A machine that runs the release pulls `latest`, so it gets the newest release without knowing its number.
The image carries the version in its `org.opencontainers.image.version` label.

| Input | Default | Effect |
|---|---|---|
| `platforms` | `linux/amd64,linux/arm64` | The processors the image runs on. |
| `lfs` | `false` | Checks out Git LFS files. |

The image takes the visibility of its repository.
So any machine can pull the image of a public repository without signing in.
A machine that pulls the image of a private repository signs in with `docker login ghcr.io` and a classic personal access token with the `read:packages` scope.

## Releasing a new version

1. Change the rules, canonical files, or workflow here, with tests.
2. Bump `version` in `pyproject.toml` and tag the commit, for example `v0.2.0`.
3. In each repository, bump `rev` in `.pre-commit-config.yaml` and the `@v0.x.y` references in `ci.yml` and `release.yml`.
4. Run `uvx pre-commit run --all-files` so `sync-files` rolls out the new canonical files.

Dependabot bumps the workflow reference and the hook revision automatically, in separate pull requests.

## License

This project is licensed under the [MIT License](LICENSE).
You may use, change, and share it, as long as every copy keeps the copyright notice and the license text.
