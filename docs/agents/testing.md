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

## Mutation

Tool: cosmic-ray, added. Status: working, last proved on cb0b2ef (96 mutants on its lines: 92
killed, none by timeout, 4 survived, 1057s).

`compost:verify` runs this over the branch's diff and sorts every surviving mutant as unprotected
behavior, equivalent, or excluded. The exclusions above apply to mutants too.

Run: the cosmic-ray steps in compost's mutation reference
(`plugins/compost/skills/verify/references/mutation.md`), from `plugins/compost`, with config
`plugins/compost/cosmic-ray.toml`. Covers compost's `scripts/` only; the other plugins, and
compost's TypeScript hooks and workflows, get only `compost:build`'s walk by hand.

Sorted on cb0b2ef: `thin.py`'s `sys.path` filter mutated to `<` and `>` was unprotected (a test
now checks every other entry stays); `- baseline.named` to `^` is equivalent, since `named` only
holds tests from `everyone`; `strays[0]` to `strays[-1]` only changes which stray the error names.

Sorted earlier, on 861127d: both survivors there are `session()`'s `concurrency=8` default in
`scripts/jevtools/core.py`, mutated to 7 and 9: equivalent, since they change throughput only and
no correctness test can tell 7, 8 and 9 apart. Tuning constants are sorted one at a time, not
excluded as a pattern; where a limit has an edge that breaks behavior (0, negative), test the edge.
