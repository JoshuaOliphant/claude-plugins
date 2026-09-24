---
name: build
description: Implements one unblocked issue in a worktree and fits its tests into the suite that already exists. Use when the user says "build #12", "work on this issue", "pick up the next ticket", "fix this and add tests", or "write the tests for this change", or when compost:implement hands over an issue.
---

# Build

Take one unblocked issue from the tracker to a committed change whose acceptance criteria are
each proven by a test. The tests go into the suite that is already there. The usual failure is a
fresh test file per feature, with its own fixtures, its own mocks, and cases that re-prove what a
neighbouring test already proves. A second suite growing beside the first costs more upkeep and
makes behavior harder to find. What this skill keeps from test-driven development is one property:
no test counts until you have seen it fail for the right reason.

## Steps

1. **Read the issue.** Find the tracker in `docs/agents/issue-tracker.md`. If that file is
   missing, run `compost:setup` now, then continue. Read the acceptance criteria (AC-N), the Files
   and Interfaces blocks, and the "Blocked by" links. Confirm every blocker is closed; if one is
   open, pick another issue or report the block. Read `CONTEXT.md` and any ADR in `docs/adr/`
   that touches the area, so names in code and tests match the domain's words.

2. **Isolate the work.** Check for existing isolation before creating anything:

   ```bash
   git_dir=$(cd "$(git rev-parse --git-dir)" && pwd -P)
   common_dir=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
   git rev-parse --show-superproject-working-tree   # prints a path only inside a submodule
   ```

   If `git_dir` differs from `common_dir` and you are not in a submodule, you are already in a
   worktree: work there. Otherwise create one without asking, branched from the current HEAD:
   `git worktree add .worktrees/<issue>-<slug> -b <issue>-<slug> HEAD` after
   `git check-ignore -q .worktrees/` confirms the directory is ignored. The harness's worktree tool
   (such as `EnterWorktree`) branches from the default branch, not from HEAD, so a feature branch's
   earlier work would be missing; use it only to enter a worktree you created this way. Install
   dependencies with the project's own tool and run the suite once for a baseline. A red baseline
   makes every later failure ambiguous, and it is pre-existing by definition: file an issue for
   each failing test, fix one in its own `fix:` commit only if it blocks a gate, and post a ruling
   on this issue saying which failures you are carrying.

3. **Survey the suite before writing any test.** Find what exists to build on:
   - fixtures, factories, and builders (`conftest.py`, `tests/factories*`, `tests/helpers*`)
   - parametrized tables (`grep -rn "mark.parametrize" tests/`)
   - the tests that already exercise the code you will change: grep for its symbols
   - how tests are named, grouped, and split across files

   Write a placement map with one line per AC: the file and test it lands in, and the fixtures
   it uses. Once the tests exist, post the map as an issue comment, one line per AC-N with its
   test node id, so `compost:verify` reads it instead of guessing.

4. **Place each acceptance criterion.** Ask Jev first: run `find-test` with the repo and every
   AC-N ([jev](references/jev.md)). `extend` names the test that already covers the criterion;
   `add-beside` names the one to write next to. Read the named test before you act on it. Exit 3
   means Jev is unavailable: place it from your survey. Either way, take the first of these that fits:
   1. Change the expectation in a test that already covers the behavior.
   2. Add a case to an existing parametrized table.
   3. Write a test in the existing file, on existing fixtures. Extend a fixture or factory with a
      parameter before writing another.
   4. Add a fixture only when nothing fits, and put it beside the ones it resembles.

   A test that duplicates a fixture, or re-covers behavior another test already covers, is a
   defect. Fix it the way you would fix a bug. When the change makes an existing test obsolete,
   fold what it still proves into a table and delete it. Give each case an id that names the
   behavior, such as `id="expired-at-exact-instant"`, so `compost:verify` can map AC-N to a node id.
   See [fitting a test in](references/fitting-a-test-in.md) for a worked before and after.

5. **Name the break before writing the test body.** Say which production change would make the
   test fail. If you cannot name one, the test checks nothing observable: redesign it around a
   behavior. If only a deliberate decision could fail it (a constant's value, exact wording,
   private structure), it is a change detector: test the behavior that depends on the decision.
   Derive the expected value without the code under test, from the spec, a literal, or a worked
   example. An expectation built with the code's own helpers passes no matter what the code does.
   Test your code's contract at its [seams](../../canon/seams.md), not the framework's mechanics.

6. **Mock only at system boundaries, through injection.** Sort each dependency with
   [deepen's dependency categories](../deepen/references/dependency-categories.md): mock only
   remote-but-owned and truly external ones (a service across the network, a third-party API,
   time, randomness). Local-substitutable ones, such as a database or the filesystem, run for
   real or with a local stand-in (a temp dir, an in-memory database). Pass mocks in as parameters
   or fixtures rather than patching a module path. Never mock your own modules or internal
   collaborators.
   A mock earns no assertions of its own; assert on the real component's result. A fake response
   mirrors the whole real structure, not only the fields this test reads. A method that only
   tests call belongs in test utilities, not in the production class. See
   [boundary discipline](../../canon/boundary-discipline.md).

7. **See every new or changed test fail for the right reason.** Whether you write the test or
   the code first is your call. Before the change counts, each new or changed test must have run
   red against code without the change, failing on its assertion with the message you expected.
   An import error, a typo, or a fixture that rejects a keyword argument is the wrong reason; fix
   the test and run it again. If you wrote the code first, undo the production edit in the
   working tree, run the test, watch it fail, and reapply. When a failing test is impractical
   (a rendering detail, a race, a service that cannot be faked), say why in an issue comment and
   run the closest executable check instead, such as a script against the real code or the
   bundled `/run` driving the app. Record its output.

8. **Refactor inside the change.** Leave the code you touched clean. Replace rather than
   deprecate: no compatibility shims, no `_old` or `_legacy` twins, no flag keeping the previous
   path alive. The old path and its callers go in the same commit. Wide mechanical renames that
   cannot land at once belong to `compost:slice` as an
   [expand-contract](../../canon/expand-contract.md) sequence, not to a shim here.

9. **Mutate the code in your head.** For each realistic mutation, name the test that fails:
   - a wrong constant, argument, or comparison (`>` for `>=`)
   - the wrong branch taken
   - a missing state change or side effect
   - an empty or default return
   - missing validation for zero, empty, None, unauthorized, or malformed input

   A mutation that nothing catches is an unprotected behavior. Close it with a case in an
   existing table or test, following step 4 again.

10. **Commit with the issue number.** Before committing, ask Jev whether a new or changed test
    re-covers an existing one: run `duplicate-test` with the base the branch started from
    ([jev](references/jev.md)), and fold every `fold into <test>` into that test as step 4 says.
    Exit 3: compare each new test against its neighbours in the file yourself. Run the full
    suite. A failing test outside the change gets run on the base SHA first. Red there, it is
    pre-existing: handle it as a red baseline in step 2. Green there, your change broke it: hand
    it to `compost:diagnose`. Commit with a
    conventional message that names the issue, such as
    `feat(auth): expire tokens at their expiry instant (#42)`. The issue closes when its PR
    merges, not at commit. Tick this issue's own AC boxes; the parent's checklist is not yours to
    tick. Post any ruling you made on the way as an issue comment: what, why, and the cost if
    wrong.

## Next moves

- `compost:verify` when every AC has a test you have seen fail and the suite is green.
- `compost:diagnose` when a test fails for a reason you cannot explain, or a test outside the
  change passes on the base SHA and fails on yours.
- `compost:deepen` when a test cannot be placed because the interface has no usable seam.
- `compost:slice` when the issue turns out to hold more than one tracer bullet.
