# Tests and gates

## Test convention

pytest, adopted from the existing suites.

- Each plugin owns its tests: `plugins/<plugin>/tests/` (a few older plugins keep
  `scripts/test_*.py` beside the code). The `tests/` suites insert `scripts/` into `sys.path` in
  each test file.
- The repo-level scripts under `scripts/` keep theirs in `scripts/tests/`, collected by the root
  `pytest` run; each test file inserts the directory of the module it tests (`scripts/`, or
  `scripts/shared/` for the canonical shared copies) into `sys.path`.
- Experiment harnesses under `ai_docs/experiments/` keep a `test_*.py` beside the harness,
  also collected by the root run.
- Each acceptance criterion AC-N maps to a test node id or parametrize id, recorded in the
  issue's AC table.
- BDD feature files: no.

## Gates

`compost:verify` runs these in order and stops at the first failure. CI runs all three (Lint and Format through `check_all.py`).

| Gate | Command | Status |
|---|---|---|
| Repo checks | `uv run --group dev python scripts/check_all.py` (marketplace versions, shared-artifact sync, every plugin's tests, `scripts/tests` and `ai_docs/experiments`, lint, format) | passing |
| Lint | `uv run --group dev ruff check .` (run by `check_all.py`) | passing |
| Format | `uv run --group dev ruff format --check .` (run by `check_all.py`) | passing |

compost, with its 100% coverage gate and live Jev evals, moved to
[JoshuaOliphant/compost](https://github.com/JoshuaOliphant/compost) and is gated there.

## Coverage

No plugin here is gated yet; new Python still aims for 100% line coverage. It is a target, not one
to pad: when reaching it would take tests that prove nothing, bring the uncovered lines to the user.

## Mutation

Tool: compost's `thin.py survivors`, run from a compost checkout against a plugin's `scripts/`. Not
yet proved on a plugin in this repo; until it is, plugins get only `compost:build`'s walk by hand.
