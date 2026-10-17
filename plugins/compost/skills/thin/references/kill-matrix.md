# Kill matrix

A mutation run for a gate stops at the first test that fails, since one is enough to call the
mutant killed. Thinning needs every test that fails, so `thin.py matrix` runs each mutant against
all the tests whose coverage context touches its line, without `-x`, and reads each failure from
pytest's `--junitxml` report. A mutant whose run leaves no report (an import error, a timeout)
counts as killed by every test that covers its line.

## What it found on compost

Run on compost's own suite at 100% line coverage, four modules (`jevtools/spec.py`,
`jevtools/meta.py`, `jevtools/review.py`, `lint/extract.py`), 1,315 mutants:

- Line coverage alone flagged 68 of the 358 tests that run measured code as exact duplicates of
  another, and a greedy line cover kept 170 of 358.
- Of the 61 tests whose lines all sit in those modules, the matrix kept 35, called 25 redundant
  and 1 kills-nothing.
- Of the 39 tests coverage flagged among those 61, 19 kill a mutant no other test does: boundary
  rows such as `at threshold` and `just under` run the same lines and pin different behavior.
  Coverage also missed 6 tests the matrix found redundant.
- The flagged negative and rejection cases were where mutation was weakest. `is_test_path`'s
  `pkg/orders.py -> False` row killed nothing, and five `rejects bad input` rows came out
  redundant, because cosmic-ray has no operator that returns a constant or deletes a guard. Step 5
  of the skill exists for these.

Line coverage is a cheap filter, then, and a poor judge: about half its candidates were wrong.

## Cost

Each mutant costs one cosmic-ray process and one pytest process, about two seconds on a small
suite before the tests themselves run. 1,315 mutants took about 10 minutes as one run per module,
five in parallel on four cores. `--only` keeps the cost to the candidates' lines.

Mutation is in place, so parallel runs need separate trees. One git worktree per module works:

```bash
git worktree add --detach "$T/wt-<module>" HEAD
```

Run `thin.py matrix` in each with a contexts file filtered to that module, then merge the
`mutants` lists and take the union of `selected` before `verdict`. Remove the worktrees afterwards
with `git worktree remove`.

## Gotchas

- **cosmic-ray can crash on a mutant.** Its AST walk raised `AttributeError` on one mutant in
  compost's `skill_drift.py`. `thin.py` leaves out any mutant `cosmic-ray apply` can't make; a
  driver of your own needs the same guard.
- **Stale bytecode.** A mutant the same size as the original, written in the same second, can run
  as the old `.pyc`. `thin.py` gives each test run a fresh `PYTHONPYCACHEPREFIX`.
- **Coverage gates.** `--no-cov` in the test command keeps a `fail_under` in `addopts` from
  failing every mutant's run.
- **Judge only what was mutated in full.** A test outside `--only` was mutated only where it
  overlaps the candidates, so `verdict` always keeps it and never judges it.

## Other stacks

`thin.py verdict` reads any matrix of this shape, so a tool that reports every killing test can
feed it:

```json
{"selected": ["<test id>", "..."],
 "mutants": [{"id": "<mutant id>", "covering": ["<test id>"], "killers": ["<test id>"]}]}
```

Neither of these has been run by compost yet:

- **StrykerJS**: set `"disableBail": true` so every test runs against each mutant; the JSON
  reporter's `mutants[].killedBy` and `coveredBy` hold test ids, named in `testFiles`.
- **PIT**: `fullMutationMatrix=true` with XML output lists every `killingTests` per mutation,
  separated by `|`.
