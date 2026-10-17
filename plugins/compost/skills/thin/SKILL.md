---
name: thin
description: Finds tests that no longer earn their place, where every bug they would catch another test already catches, and folds or deletes them on the user's word. Per-test coverage narrows the candidates, a full mutation kill matrix judges them, and a hand-made break confirms each one before it goes. Use when the user says "thin the tests", "we have too many tests", "find duplicate tests", "which tests are redundant", "minimize the test suite", "the suite is bloated", "agents keep writing the same test", or when a suite has grown faster than the code it covers.
---

# Thin

A suite that grows by agents adding tests without reading the ones already there ends up with
many tests that pin the same behavior, each a little different in shape. Every one of them costs
a run and a change when the code moves, and none of them adds protection. Line coverage can't
find them: two tests that run the same lines can check different things, and two that check the
same thing can take different paths. A kill matrix can. Mutate the code, record every test that
fails for each mutant (not only the first), and a test whose kills another test also makes adds
nothing that mutation can see.

Mutation sees only what its operators model, so its verdict is a lead, not a ruling. On compost's
own suite, the matrix called five rejection tests redundant because the happy-path tests already
kill an inverted guard, while cosmic-ray has no operator that deletes the guard, which only the
rejection tests would catch. Every verdict gets one more check by hand before a test goes.

Jev's `duplicate-test`, which `compost:build` runs on each new test, reads tests instead of
running them, so it also judges what mutation can't see: tests over files and docs, string
assertions, tests whose lines no coverage context records. Where the two disagree, the break by
hand decides.

## Steps

1. **Start green.** Run the suite and stop if it fails: on a red baseline every mutant counts as
   killed. Read `docs/agents/testing.md` for the test command and the mutation tool. This skill
   drives cosmic-ray for Python; for another stack see [other stacks](references/kill-matrix.md#other-stacks).

2. **Record per-test coverage.** Collect which lines each test runs, then narrow to candidates:

   ```bash
   T=${TMPDIR:-/tmp}/thin && mkdir -p "$T"
   pytest --cov=<package> --cov-context=test --cov-report= -p no:cacheprovider
   coverage json --show-contexts -o "$T/contexts.json"
   uv run ${CLAUDE_PLUGIN_ROOT}/scripts/thin.py candidates "$T/contexts.json" > "$T/candidates.json"
   ```

   A candidate runs the same lines as another test, or a subset of them. `tests` counts the tests
   that ran a measured line; compare it with `pytest --collect-only -q`. The rest test files,
   docs, or another process, and the matrix can't judge them: read them yourself.

3. **Build the kill matrix.** Scope it to the candidates' lines; it runs every mutant there
   against every test that covers the line, so it costs about one suite run per mutant line:

   ```bash
   uv run --with cosmic-ray python ${CLAUDE_PLUGIN_ROOT}/scripts/thin.py matrix "$T/contexts.json" \
     --only "$T/candidates.json" --pytest-args "-q -p no:cacheprovider --no-cov" > "$T/matrix.json"
   uv run ${CLAUDE_PLUGIN_ROOT}/scripts/thin.py verdict "$T/matrix.json" > "$T/verdict.json"
   ```

   The matrix runs inside the project's environment, so its imports resolve as the tests' do. It
   first runs the covering tests unmutated and stops with exit 2 unless they all pass: under a
   broken setup, such as an interpreter without the project's packages, every run fails, every
   test kills every mutant, and the verdict would call all but one test redundant. Each mutant
   runs in a child forked from the warm process, served from memory, one per core
   ([kill matrix](references/kill-matrix.md)); files on disk never change.

4. **Read the verdict.** Each candidate is one of:
   - **keep**: it kills a mutant no other test kills (`unique` names them).
   - **redundant**: every mutant it kills, `subsumed_by` also kills; `null` means only several
     tests together cover it, so removing it is safe but removing two of that set may not be.
   - **kills-nothing**: it runs the lines but fails for no mutant.

   `minimal` is the candidates a greedy cover keeps, computed together: removing every candidate
   outside it keeps every kill, while removing two redundant tests chosen one at a time may not.

   `survived` lists mutants no test kills. They are a coverage gap, not this skill's job: hand them
   to `compost:build` as its step 10 does.

5. **Confirm each verdict by breaking the code by hand.** For every redundant or kills-nothing
   test, name the behavior only it seems to pin, then break exactly that in the code: delete the
   guard it exercises, return a constant from the predicate, drop the side effect, swap the
   message. Run the suite without the test (`--deselect <node id>`). If another test fails, the
   verdict holds. If none does, the test stays: say which break only it catches. Always confirm by
   hand, before touching the test, when it is:
   - a negative or rejection case (`returns False`, `raises`): cosmic-ray never deletes a
     statement or returns a constant;
   - an assertion on a string, a message, or rendered output: cosmic-ray never mutates string
     literals;
   - a regression test for a bug found in history (`git log -S` on its name, an issue link): the
     bug it pins may be no mutant at all.

6. **Present the plan.** Per confirmed test: delete it, or fold its case into the test that
   subsumes it as a parametrize row when it documents an input class worth naming. Lead with the
   count of tests that go and the suite time saved. When the subsumer is a broad, slow test and
   the redundant one is focused, offer the swap: keep the focused one and narrow the broad one.
   Wait for the user's yes, for all of it or test by test. Inside an unattended run, change
   nothing; post the plan where the run reports and stop.

7. **Thin, then prove nothing was lost.** Remove only tests outside `minimal`, so every mutant the
   old suite killed is still killed by construction. A fold changes a test, so it goes through
   `compost:build`'s red check: break the code as step 5 did and watch the folded row fail. Run
   the suite and the coverage gate. Commit as `test: fold tests that no mutant needed`.

## Next moves

- `compost:build` when `survived` names behavior no test protects.
- `compost:deepen` when one module draws dozens of overlapping tests: its interface is likely too
  shallow to test at, and its shape is the fix.
- `compost:verify` before calling the thinning done.
- `compost:finish` to open the pull request.
