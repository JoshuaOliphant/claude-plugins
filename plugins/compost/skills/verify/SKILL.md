---
name: verify
description: Proves a change works from fresh evidence before anyone says it does. Use before claiming done, fixed, or passing, before a commit or PR, and when the user asks "is this ready", "verify this", "prove it works", "are the acceptance criteria met", "check coverage", or "what could this break".
---

# Verify

A claim that work is done is worth only the evidence behind it, and the evidence has to come from
this tree, run now. A remembered green run, a subagent's "all tests pass", or "it should work"
is not evidence. This skill produces the evidence: the gates run fresh, every acceptance
criterion tied to a passing test, and the one fact the change's safety rests on proven by running
code. Read [prove it works](../../canon/prove-it-works.md) for the principle behind every step.

## Steps

1. **Find the gates.** Read the gates `compost:setup` recorded in `docs/agents/testing.md`: the
   test command, the coverage threshold and any recorded exclusions, linters, and type checkers.
   If the file is missing, run `compost:setup` now, then continue. Until it exists, the
   project's CI workflow defines green: what `.github/workflows/*` runs, plus any `pre-commit`,
   `Makefile` or `justfile` check target.

2. **Run the full suite and every gate, fresh.** Run them in this worktree now, not earlier and
   not somewhere else. Read each exit code and the whole output. Stop at the first failure and
   read its log before touching anything else: the first failing log carries the information,
   and later failures are often its echoes. A failing test outside the change gets run on the
   base SHA first. Red there, it is pre-existing: file an issue, fix it in its own `fix:` commit
   only if it blocks a gate, and post a ruling. Green there, the change broke it: fix it if the
   cause is plain; otherwise hand it to `compost:diagnose`. A warning the gate prints is a finding too: fix it, or say why it stays.
   When a subagent did the work, read `git diff` yourself rather than trusting its report.

3. **Hold the coverage gate.** The gate is 100% line coverage, for example
   `uv run pytest --cov --cov-report=term-missing --cov-fail-under=100`. For each missing line:
   - It is behavior: go back to `compost:build` and fit a test in.
   - It is dead: delete it.
   - Covering it would take a test that proves nothing (asserting a constant, re-testing the
     framework, a `__main__` guard): stop and bring the user the file and line numbers, with a
     proposed exclusion (`exclude_also` in the coverage config, or a `pragma: no cover` on that
     line) or a lower threshold. Do not pad the suite to reach the number. When running
     unattended, under `compost:implement`, or as a worker, post the proposal as a ruling comment
     on the issue, list it in the PR's Risk section, and continue; the user decides at
     `compost:finish`.

4. **Map every acceptance criterion to a passing test.** Build a table from this run's results:
   AC-N, the test's node id, and pass or fail. Find the tests in the placement map
   `compost:build` posted on the issue (AC-N to node id). A criterion with no test is unmet, with no judgment call. So is one
   whose test was skipped, deselected, or marked xfail in this run, because a test that did not
   run proves nothing.

5. **Prove the one fact the change is safe because of.** Most changes that look risky are safe
   because of one fact, such as "this call only evicts entries that are already expired". Name
   it, then push it as far down this ladder as is cheap:
   1. Asserted: you said so. Worth nothing on its own.
   2. Cited: you pointed at the `file:line`, in this repo or in the library's source at the pinned
      version.
   3. Walked: you traced the bad case step by step and showed it cannot happen.
   4. Ran: a script or test calls the real code and fails loudly if the fact is false.
   5. Reproduced live: the running app shows it. Use the bundled `/run` to start and drive it.
      The bundled `/verify` does the same but only the user can run it; suggest it when they
      want to see it themselves.

   Look where grep stops: the library's own source, JSON a service returns, a database column, a
   feature flag, another program reading the same bytes. Report the rung you reached. Below
   "ran", call the fact unproven. See [the proof ladder](references/proof-ladder.md) for examples.

6. **Make silent checks prove they ran.** A check that prints nothing when it fails looks the
   same as one that never ran. Before counting it as a pass, show it did work: the number of
   tests collected, the number of files linted, or one run where it caught a planted defect.
   Common cases, such as pytest collecting nothing or coverage measuring the wrong package, are
   in [the proof ladder](references/proof-ladder.md).

7. **Check the comments in the diff.** For Python, run the `jev-lint` skill when it is available.
   If it reports that `TYPESAFE_API_KEY` is not set, say so and do the manual pass. Otherwise read every comment the diff adds. Keep only:
   - legal or license headers
   - behavior forced by an external dependency, platform, or protocol we cannot reshape
   - a lint suppression whose rule is wrong for that line (a suppression hiding a correctness or
     safety rule means the code needs fixing, not the suppression)
   - doc comments that define a public API contract
   - issue or RFC links for a constraint the code cannot express

   Delete the rest: narration, banners, commented-out code, workaround explanations, and history
   ("changed from X"). A comment explaining a surprise in our own code means the code needs a
   better name, an extracted function, or a type. Change the code and drop the comment.

8. **Report the evidence.** Give the commands and their counts (`214 passed, 0 failed`), the
   coverage result and any proposed exclusion, the AC table, the safety fact with its rung and
   the proof output, and the comments removed. Post the AC table on the issue; on a re-run, edit
   the AC-table comment you posted before instead of adding another. Say "done" only
   when every row is met and every gate is green. Otherwise state the actual status.

## Next moves

- `compost:review` when every gate is green and every AC is met.
- `compost:build` when an AC is unmet, or a coverage gap is real behavior.
- `compost:diagnose` when a gate fails and the cause is not plain.
- `compost:finish` when review findings are addressed and this run is on the final commit.
