# dev-standards

This repository is the single source of the conventions shared by the Discord bots, the api-* services, their templates, and the Lua mods.
Read `README.md` first, because it is the rulebook that every other repository points to.

## Layout

* `src/dev_standards/prose/` holds the check-prose hook. `rules.py` has the rules, `blocks.py` splits docstrings and block comments, and the other modules turn Python, Lua, or Markdown into paragraphs.
* `src/dev_standards/config.py` reads the settings from `pyproject.toml`, or from `dev-standards.toml` in a repository without one, and tells a repository's languages.
* `src/dev_standards/sync.py` and `src/dev_standards/canonical/` hold the sync-files hook and the canonical parts it builds each file from. A part without a language suffix, such as `gitignore.block`, reaches every repository, and one with a suffix, such as `gitignore.python.block`, reaches only that language's repositories.
* `src/dev_standards/template.py` holds the template-check command.
* `.github/workflows/python-ci.yml` and `.github/workflows/lua-ci.yml` are the reusable CI workflows the Python and Lua repositories call.
* `.github/workflows/docker-publish.yml` is the reusable workflow that publishes a release's Docker image.

## Working here

* Run `uv run pytest`, `uv run mypy src`, and `uvx pre-commit run --all-files` before proposing a change.
* A new prose rule needs parametrized cases in `tests/test_prose.py`, including cases that must not trigger it.
* A change to a canonical file or the workflow reaches other repositories only after a new tag. Bump `version` in `pyproject.toml` together with it.
* Keep the package free of third-party runtime dependencies, because pre-commit installs it into every repository's hook environment.
