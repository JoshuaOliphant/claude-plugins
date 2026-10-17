# Kill matrix

A mutation run for a gate stops at the first test that fails, since one is enough to call the
mutant killed. Thinning needs every test that fails, so `thin.py matrix` runs each mutant against
all the tests whose coverage context touches its line, without `-x`, and reads each failure from
pytest's `--junitxml` report. A mutant whose run leaves no report (an import error, a timeout)
counts as killed by every test that covers its line.

## What it found on compost

Run on compost's own suite at 100% line coverage, five modules (`jevtools/spec.py`,
`jevtools/meta.py`, `jevtools/review.py`, `lint/extract.py`, `skill_drift.py`), 1,577 mutants:

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

A short test run is mostly startup: starting Python, importing pytest, collecting. So `thin.py`
imports pytest once, then forks a child per mutant that serves the mutated module from memory
through an import hook. Nothing on disk changes, so children run side by side, one per core.
On `stop_guard.py`'s 100 covered mutants, every runner gave the same killers for every mutant:

| Runner | Wall |
| --- | --- |
| `cosmic-ray apply`, then a fresh pytest process, per mutant | 272 s |
| fork after import, mutant in memory, 1 worker | 47 s |
| the same, 4 workers | 14 s |

`--only` keeps the count to the candidates' lines; on suites with slow tests, running only the
tests that cover each line is what keeps each mutant cheap.

## Gotchas

- **A broken setup reports perfect tests.** Run under an interpreter without pytest or the
  project's packages, every mutant's run errors, and an error counts as a kill. For a gate that
  reads as a perfect score; for thinning it is worse, since every test then kills every mutant and
  all but one look redundant. `thin.py matrix` runs the covering tests unmutated first and stops
  with exit 2 unless every one passes.
- **stdin must be closed.** A mutant can turn a branch into one that reads stdin, and a child that
  inherits an open one blocks until its timeout: one measured run went from 22 seconds to 172 with
  the same verdicts. Each child reads `/dev/null`.
- **cosmic-ray can crash on a mutant.** Its AST walk raised `AttributeError` on one mutant in
  compost's `skill_drift.py`. `thin.py` leaves out any mutant cosmic-ray can't make; a driver of
  your own needs the same guard.
- **No stale bytecode.** Mutants never touch the file, and children don't write `.pyc` files, so a
  mutant can't run as the original's bytecode.
- **Coverage gates.** `--no-cov` in `--pytest-args` saves each run the coverage work. The verdict
  reads the junit report, not the exit code, so a `fail_under` in `addopts` doesn't spoil it.
- **Tests that share a port or a fixed path.** Children run side by side, each with its own
  `--basetemp`, but anything else two tests both claim can fail one of them for no mutant's sake,
  which reads as a kill. Run such a suite with `--workers 1`.
- **Judge only what was mutated in full.** A test outside `--only` was mutated only where it
  overlaps the candidates, so `verdict` always keeps it and never judges it.
- **The parent must not import the code under test.** A child serves the mutant through an import
  hook, which only sees modules imported after the fork. `thin.py` imports pytest before forking
  and nothing from the project.

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
