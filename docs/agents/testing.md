# Tests and gates

## Test convention

pytest, adopted from the existing suites.

- Each plugin owns its tests: `plugins/<plugin>/tests/` (a few older plugins keep
  `scripts/test_*.py` beside the code). Shared fixtures live in that plugin's
  `tests/conftest.py`, which also puts the plugin's `scripts/` on the import path.
- Plugins with their own `pyproject.toml` (compost, review-diff, jev-lint) run their suite from
  their directory with their own dev group and coverage gate.
- Each acceptance criterion AC-N maps to a test node id or parametrize id, recorded in the
  issue's AC table.
- BDD feature files: no.

## Gates

`compost:verify` runs these in order and stops at the first failure. CI runs the first three.

| Gate | Command | Status |
|---|---|---|
| Repo checks | `uv run --group dev python scripts/check_all.py` (marketplace versions, shared-artifact sync, every plugin's tests) | passing |
| compost coverage | `cd plugins/compost && uv run --group dev pytest` | passing |
| review-diff coverage | `cd plugins/review-diff && uv run --group dev pytest` | passing |
| jev-lint coverage | `cd plugins/jev-lint && uv run --group dev pytest` | passing (not in CI yet) |
| Lint | `uv run --group dev ruff check .` | broken: 41 errors, first `plugins/compound-knowledge/tests/test_resolve_paths.py:20:29 E702` (34 are E702 in compound-knowledge and understand tests) |
| Format | `uv run --group dev ruff format --check .` | broken: 20 files would be reformatted |

The live Jev evals in compost (`pytest -m jev`) are not a gate: they need a TypeSafe key and the
private compost-evals checkout.

## Coverage

Threshold: 100% line coverage, enforced per plugin by `fail_under = 100` in the plugin's own
`pyproject.toml` (compost, review-diff, jev-lint). Plugins without one are not gated yet; new
Python in them still aims for 100%. It is a gate, not a target to pad: when reaching it would take
tests that prove nothing, bring the uncovered lines to the user with a proposed exclusion or a
lower threshold. When running unattended, under `compost:implement`, or as a worker, post the
proposal as a ruling comment on the issue, list it in the PR's Risk section, and continue; the
user decides at `compost:finish`.

Exclusions agreed so far:

- `if __name__ == "__main__":` guards (`exclude_also` in compost's and jev-lint's coverage
  config; review-diff has none).
