---
name: review
description: Reviews a verified change with subagents on two axes, Standards and Spec, then works through the findings that survive. Run it after compost:verify passes on every issue, without being asked. Use when someone says "review this branch", "review my changes", "check this against the issue", "is this ready to merge", "does the approach fit", or "I want to sign off on the diff myself".
---

# Review

A change that passes its tests can still break the repo's rules or quietly miss what the issue asked for. Review catches both before the change reaches `compost:finish`. Subagents do the reviewing so the reviewer never shares the author's context, and each finding has to survive a skeptic before it costs you a fix.

Run this after `compost:verify` passes on every issue. Nobody needs to ask.

## Steps

1. **Run the review workflow.** Run `/compost:review-changes` with `{base, issue}`. Leave `base` out to review against the merge-base with the default branch; pass `issue` when you know the issue number, since the Spec axis needs its AC-N. The workflow scopes the diff, runs a Standards reviewer and a Spec reviewer as `compost:reviewer` subagents in parallel, and hands every finding to a skeptic told to refute it. Pass `skeptics: 3` for a branch where a false finding would be expensive; a finding then survives only when most skeptics uphold it.

   If the workflow reports an empty diff or an unresolvable base, fix that first: commit the work, or pass the right base. If it skipped the Spec axis because no spec was found, say so in the issue comment in step 6. A change reviewed on one axis has been half reviewed.

2. **Keep the two axes apart.** Read the Standards and Spec survivors side by side. Don't merge them into one ranked list: code can follow every standard and still build the wrong thing, and one axis must not mask the other. Skim the refuted lists too. When a skeptic refuted a blocker with reasoning you can see is wrong, check the code yourself and treat the finding as a survivor if it holds.

3. **Verify each survivor against the code before you act on it.** A survivor is a claim, not an order. For each one:
   - Restate what it asks for in one line, in the domain's terms.
   - Open the file at the cited line and check the claim against the code, the tests, and the callers.
   - If it asks for something to be "done properly" (configurable, generalised, more layers), grep for a caller that needs it first. No caller means you push back: the extra code is speculative generality, the thing [subtract before you add](../../canon/subtract-before-you-add.md) warns against.
   - If it contradicts a ruling already logged on the issue, or an ADR, the ruling stands until someone supersedes it. Push back and cite the ruling.

   Push back with evidence, not tone: the file:line that shows the reviewer wrong, the test that already covers the case, the caller that doesn't exist. When a finding is right, fix it and say what changed. Skip "good catch" and "you're right"; the fix shows you heard it. When you pushed back and then find you were wrong, say so in one line and fix it.

4. **Fix the survivors that hold, one at a time.** Blockers first, then the quick fixes, then anything that reshapes code. Fix at the root ([fix root causes](../../canon/fix-root-causes.md)), and when a fix replaces an interface, replace it: the old code goes in the same change, with no shim left behind. After each fix that changes behaviour, run the tests that cover it.

5. **Re-verify.** Once the fixes are in, run `compost:verify` again in full: suite, gates, the AC-N map. If the fixes changed behaviour or touched files the first review didn't see, run `/compost:review-changes` once more. A finding you pushed back on that comes back from a fresh reviewer deserves a second look, not a second refusal by reflex.

6. **Record the outcome on the issue.** Post one comment: what each axis found, what you fixed (with the commit), what you pushed back on and the evidence, and whether the Spec axis ran. That comment is the ruling log `compost:finish` summarises into the PR.

## When the branch is structurally risky

Standards and Spec both judge the change against a reference. Neither asks whether the approach itself was the right one. For a branch that adds a module boundary, a new data flow, a new external dependency, shared or global state, or a change that crosses bounded contexts, have a separate agent judge approach fit. This is opt-in: most issues don't need it.

Write a problem statement that describes only the problem, never the solution: what should work differently afterward, or what is broken. Any hint about the mechanism biases the judge toward the code it is about to read. Then spawn one subagent with the prompt in [approach fit](references/approach-fit.md). It reads the codebase as it was at the base, designs its own approaches before it sees the diff, then compares. Treat its verdict like a survivor from step 3: verify it, and if it names a better approach you agree with, hand the design question to `compost:deepen`.

For a large or ambiguous change, `vet` is a further independent pass over the diff and the conversation. Use it when the scope is wide enough that two focused reviewers could miss something between them.

## When the user wants to sign off themselves

Some changes the user wants to read with their own eyes. When they say so, run `/review-diff` from the review-diff plugin. It opens the branch diff in a local browser for inline, merge-request style comments and waits while they review. Their comments are the user's own review: understand each, ask about anything unclear before changing code, then fix, re-verify, and record them on the issue as in steps 4 to 6.

## Next moves

- `compost:finish` when no survivors remain and verify passes.
- `compost:verify` after any fix, before you call the review done.
- `compost:diagnose` when a finding exposes a defect whose cause you can't see from the cited line.
- `compost:deepen` when approach fit, or a cluster of Standards findings in one module, says the design is the problem.
- `compost:build` when a Spec finding shows an AC-N that was never built.
