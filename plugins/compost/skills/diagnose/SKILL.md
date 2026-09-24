---
name: diagnose
description: Finds a bug's root cause by first building a fast, deterministic check that goes red on it, then testing ranked hypotheses one variable at a time. Use before proposing any fix, when something is broken, throwing, failing, flaky, slow, or regressed - "debug this", "diagnose", "why is this failing", "this test is flaky", "it broke after the upgrade", "it only fails after a restart", "this got slow" - or when a defect turns up mid-implementation.
---

# Diagnose

A bug is found by a feedback loop, not by reading code until a theory feels right. With a check that
goes red on this bug and green once it is gone, bisection, hypotheses, and instrumentation all become
mechanical; without one, every fix is a guess and the guesses pile up as symptom patches. So the loop
comes first, the theory second, and the fix last, at the root. The why is in
[fix root causes](../../canon/fix-root-causes.md) and [prove it works](../../canon/prove-it-works.md).

## Steps

1. **Read before you touch anything.** Read the whole error and stack trace, warnings included; they
   often name the fault outright. Read `CONTEXT.md` and any ADRs in `docs/adr/` for the area so you
   use the project's names for things. Check what changed recently: `git log` and `git diff` over the
   paths involved, dependency bumps, config and environment changes.

2. **Build the feedback loop.** This is the skill; spend disproportionate effort here. You are done
   when you can name one command you have already run that is:
   - **Red-capable**: it drives the real code path and asserts the user's exact symptom, so it can
     catch this bug. "Runs without erroring" does not qualify.
   - **Deterministic**: same verdict every run. For a flaky bug, a pinned, high reproduction rate.
   - **Fast**: seconds, not minutes.
   - **Agent-runnable**: it runs unattended. A human in the loop only through
     [`scripts/hitl-loop.sh`](scripts/hitl-loop.sh).

   Work down the ladder in [references/feedback-loops.md](references/feedback-loops.md) (failing
   test, HTTP script, CLI diff, browser script, trace replay, harness, fuzz, bisection, differential,
   human-driven script), then tighten it: faster, sharper assertion, more deterministic. If you catch
   yourself forming a theory before this command exists, stop and go back to building it.

   If you truly cannot build one, say so, list what you tried, and ask for one of: access to an
   environment that reproduces it, a captured artifact (log dump, HAR, core dump, timestamped screen
   recording), or permission to add temporary instrumentation in production. Do not hypothesise
   without a loop. When running unattended, under `compost:implement`, or as a worker, post that
   request as a ruling comment on the issue, list it in the PR's Risk section, and carry on with
   the rest of the work; the user decides at `compost:finish`.

3. **Reproduce and minimise.** Run the loop and watch it go red. Confirm it is the failure the user
   described and not a neighbouring one; the wrong bug gets the wrong fix. Record the exact symptom.
   Then shrink the scenario: cut inputs, callers, config, data, and steps one at a time, re-running
   after each cut, until every remaining element is load-bearing. The minimal repro narrows the
   hypotheses and becomes the regression test.

4. **Trace to the origin.** Where the error surfaces is rarely where it starts.
   - When the failure is deep in a call chain, trace backward: what called this with the bad value,
     and what called that, until you reach the code that first produced it.
   - When several components are involved (CI, build, service, database), log what enters and leaves
     each one in a single run to find which one breaks before reading any of them closely.
   - When it only fails after a restart, suspect persistent state before code: config files, caches,
     lock files, serialized state. If clearing a state file restores behaviour, the fix is validating
     that state where it is loaded.
   - When similar code works, list every difference between the working and broken paths.

   Techniques, including finding the test that pollutes shared state, are in
   [references/tracing.md](references/tracing.md).

5. **Rank 3 to 5 falsifiable hypotheses before testing any.** One hypothesis anchors you on the
   first plausible idea. Each states its prediction: "If X is the cause, then changing Y makes the bug
   disappear and changing Z makes it worse." A hypothesis without a prediction is a hunch; sharpen it
   or drop it. Post the ranked list where the user will see it (the issue, when there is one) and
   carry on; if they re-rank from domain knowledge, take it.

6. **Probe one variable at a time.** Every probe maps to one prediction. Prefer a debugger or REPL,
   then targeted logs at the seams that tell hypotheses apart; never log everything and grep. Tag
   every debug line with a unique prefix such as `[DEBUG-a4f2]` so cleanup is one grep. For a
   performance regression, measure a baseline first (timer, profiler, query plan) and bisect against
   it; logs rarely find perf bugs.

   When hypotheses are independent and their probes don't share files or state, test them at once:
   one subagent per hypothesis, each in its own worktree, or teammates when agent teams are enabled.
   An isolated worktree starts from the default branch, not the code you are debugging, so give each
   the SHA under investigation and have it run `git switch -C <branch> <SHA>` before probing. Give
   each the loop command, its hypothesis and prediction, and ask for the probe output and a
   verdict. Probes that touch the same files run in order.

7. **Fix at the root, with a regression test at a real seam.** A real seam (Feathers,
   [seams](../../canon/seams.md)) is one where the test exercises the bug as it happens at the call
   site: the multi-caller chain, the real data shape. A test at a seam too shallow to reproduce the
   chain gives false confidence. If no real seam exists, that is the finding: note it and hand it to
   `compost:deepen`.

   With a seam, fit the minimised repro into the existing suite as a test beside its neighbours,
   watch it fail, apply the fix, watch it pass, then re-run the original loop against the full
   scenario. Fix the pattern, not the instance: search for the same mistake elsewhere and fix those
   too.

   Don't silence a symptom with a guard. A null check that stops a crash leaves the bad value in
   flight. Validation belongs at the system boundary ([boundary discipline](../../canon/boundary-discipline.md)),
   so the fix goes where the bad value is born. Layered validation at every hop is for critical paths
   the user has named (payments, data deletion, auth, and the like); see
   [references/critical-paths.md](references/critical-paths.md).

8. **After three failed fixes, stop fixing.** Count them. A third fix that doesn't hold, or fixes
   that each surface a new problem somewhere else, or a fix that needs sweeping rework to land, means
   the design is wrong, not the hypothesis. Write up the pattern (what each fix revealed, which shared
   state or coupling keeps showing up) and take it to `compost:deepen`. If reshaping it changes an
   approved spec, bring it to the user; that is an architectural approval.

9. **Clean up and record.** Before calling it done:
   - The original loop no longer reproduces the bug.
   - The regression test passes, or the missing seam is written down.
   - `grep` for your debug prefix returns nothing; throwaway harnesses are deleted.
   - The confirmed hypothesis goes in the commit message, and on the issue when there is one, so the
     next person debugging here learns from it.

   If the investigation shows the cause is truly environmental or external (a timing dependency on
   another service, a platform quirk), record what you ruled out, handle it at the boundary with a
   clear error or bounded retry, and add the logging that would catch it next time. Most "no root
   cause" verdicts are unfinished investigations, so check the trace once more first.

## Next moves

- `compost:implement` when the defect came from an issue in flight: return to it with the fix in.
- `compost:verify` when the fix is in and the project's gates need running.
- `compost:deepen` when there is no real seam for the regression test, or three fixes have failed.
- `compost:slice` when the root cause needs more than one change to put right.
- `compost:review` when this was a standalone fix and it is ready for review.
