# Tests and gates

## Test convention

pytest, adopted from the existing suites.

- Each plugin owns its tests: `plugins/<plugin>/tests/` (a few older plugins keep
  `scripts/test_*.py` beside the code). compost keeps shared fixtures in `tests/conftest.py`,
  which also puts its `scripts/` on the import path; the other `tests/` suites insert `scripts/`
  into `sys.path` in each test file.
- Plugins with their own `pyproject.toml` (compost) run their suite from
  their directory with their own dev group and coverage gate.
- Each acceptance criterion AC-N maps to a test node id or parametrize id, recorded in the
  issue's AC table.
- BDD feature files: no.

## Gates

`compost:verify` runs these in order and stops at the first failure. CI runs all four (Lint and Format through `check_all.py`).

| Gate | Command | Status |
|---|---|---|
| Repo checks | `uv run --group dev python scripts/check_all.py` (marketplace versions, shared-artifact sync, every plugin's tests, lint, format) | passing |
| compost coverage | `cd plugins/compost && uv run --group dev pytest` | passing |
| Lint | `uv run --group dev ruff check .` (run by `check_all.py`) | passing |
| Format | `uv run --group dev ruff format --check .` (run by `check_all.py`) | passing |

The live Jev evals in compost (`pytest -m jev`) are not a gate: they need a TypeSafe key and the
private compost-evals checkout.

## Coverage

Threshold: 100% line coverage, enforced per plugin by `fail_under = 100` in the plugin's own
`pyproject.toml` (compost). Plugins without one are not gated yet; new
Python in them still aims for 100%. It is a gate, not a target to pad: when reaching it would take
tests that prove nothing, bring the uncovered lines to the user with a proposed exclusion or a
lower threshold. When running unattended, under `compost:implement`, or as a worker, post the
proposal as a ruling comment on the issue, list it in the PR's Risk section, and continue; the
user decides at `compost:finish`.

Exclusions agreed so far:

- `if __name__ == "__main__":` guards (`exclude_also` in compost's coverage config).
