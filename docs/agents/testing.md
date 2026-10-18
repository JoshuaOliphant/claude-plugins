# Tests and gates

## Test convention

pytest, adopted from the existing suites.

- Each plugin owns its tests: `plugins/<plugin>/tests/` (a few older plugins keep
  `scripts/test_*.py` beside the code). compost keeps shared fixtures in `tests/conftest.py`,
  which also puts its `scripts/` on the import path; the other `tests/` suites insert `scripts/`
  into `sys.path` in each test file.
- The repo-level scripts under `scripts/` keep theirs in `scripts/tests/`, collected by the root
  `pytest` run; each test file inserts the directory of the module it tests (`scripts/`, or
  `scripts/shared/` for the canonical shared copies) into `sys.path`.
- Plugins with their own `pyproject.toml` (compost) run their suite from
  their directory with their own dev group and coverage gate.
- Each acceptance criterion AC-N maps to a test node id or parametrize id, recorded in the
  issue's AC table.
- BDD feature files: no.

## Gates

`compost:verify` runs these in order and stops at the first failure. CI runs all four (Lint and Format through `check_all.py`).

| Gate | Command | Status |
|---|---|---|
| Repo checks | `uv run --group dev python scripts/check_all.py` (marketplace versions, shared-artifact sync, every plugin's tests and `scripts/tests`, lint, format) | passing |
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

Tool: thin.py survivors, compost's own. Status: working, last proved on this tool's own branch
(#123): 219 mutants on 134 changed lines of `scripts/thin.py`, 184 killed, 11 survived, 1 timeout,
23 crashed, 348s.

`compost:verify` runs this over the branch's diff and sorts every surviving mutant as unprotected
behavior, equivalent, or excluded. The exclusions above apply to mutants too.

Run: the Python steps in compost's mutation reference
(`plugins/compost/skills/verify/references/mutation.md`) from `plugins/compost`, with
`--paths scripts` and the plain `pytest` collecting contexts for every module `addopts` covers
(`uv run --group dev python -m pytest -q -p no:cacheprovider --cov-context=test --cov-report= --cov-fail-under=0`).
Covers compost's `scripts/` only; the other plugins, and compost's TypeScript hooks and workflows,
get only `compost:build`'s walk by hand.

Sorted on #123: the 11 survivors are equivalent. `workers` 1 to 2 on the baseline's single job;
`strays[0]` to `[-1]` and `- named` to `^`, as on cb0b2ef; `len(new) > 1` to `!= 1`, since a hunk
range has one or two parts; `k != "args"` to `>` or `is not`, and `==` to `is` on "survivors", which
string ordering and interning keep the same; `is TIMED_OUT` to `==`, since TimedOut has no `__eq__`;
stderr's `flush`, and the JSON `indent`. Tuning constants are sorted one at a time, not excluded as a
pattern; where a limit has an edge that breaks behavior (0, negative), test the edge.
