# dev-standards

This repository is the single source of the conventions shared by the Discord bots, the api-* services, and their templates.
Read `README.md` first, because it is the rulebook that every other repository points to.

## Layout

* `src/dev_standards/prose/` holds the check-prose hook. `rules.py` has the rules, and the other modules turn Python or Markdown into paragraphs.
* `src/dev_standards/sync.py` and `src/dev_standards/canonical/` hold the sync-files hook and the canonical files it writes.
* `src/dev_standards/template.py` holds the template-check command.
* `.github/workflows/python-ci.yml` is the reusable workflow that every repository calls.

## Working here

* Run `uv run pytest`, `uv run mypy src`, and `uvx pre-commit run --all-files` before proposing a change.
* A new prose rule needs parametrized cases in `tests/test_prose.py`, including cases that must not trigger it.
* A change to a canonical file or the workflow reaches other repositories only after a new tag. Bump `version` in `pyproject.toml` together with it.
* Keep the package free of third-party runtime dependencies, because pre-commit installs it into every repository's hook environment.
