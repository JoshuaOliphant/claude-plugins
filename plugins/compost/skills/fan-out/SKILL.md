---
name: fan-out
description: Settles a contested design or an unclear cause by running several independent attempts in parallel, judging them against each other on a rubric, and synthesizing the winner. Use when one attempt would lock in the wrong shape or anchor on the first theory - "try a few approaches", "compare designs", "arena this", "swarm this", "race these", "design it twice", "which of these hypotheses holds", "get competing takes" - or when a ruling has more than one defensible answer.
---

# Fan out

One attempt at a non-trivial design locks in its first shape, and one investigator anchors on the
first plausible cause. Several independent attempts at the same problem, judged side by side, show
what the problem allows: where they converge you can ship with confidence, and where they differ the
best parts of the losers are usually worth grafting into the winner. This is Ousterhout's "design it
twice" ([deep modules](../../canon/deep-modules.md)) run in parallel, and the same move for
hypotheses: the theory that survives the others' attempts to disprove it is the one to trust.

Spawn the attempts without asking. The cost is tokens; the payoff is not building the wrong thing.

## Steps

1. **Frame the contract.** Every attempt gets the same task, so the task is the contract. State:
   - the artifact each attempt produces (an interface sketch, a prototype on a branch, a
     root-cause verdict with its evidence, a written design);
   - the shared grounding every attempt reads (the issue, the spec, `CONTEXT.md` terms, the files
     involved), as pointers;
   - the rubric: 3 to 6 concrete, gradeable criteria for this task, such as "callers need no
     knowledge of the storage format" or "explains all three observed symptoms". The rubric is for
     judging; attempts see only the task.

2. **Choose the shape and the number.**
   - **Race:** N attempts at the identical brief. Use it when the task is generation-bound and
     variety comes from the attempt itself.
   - **Directions:** each attempt is assigned a different stance, or one hypothesis per
     investigator. Use it for interface design and for diagnosis with several live hypotheses. For
     an interface, take the stances and the brief from `compost:deepen`'s
     [design it twice](../deepen/references/design-it-twice.md).
   Three attempts is the usual starting point; add one per extra direction worth exploring.

3. **Spawn them all in one message.** Each attempt writes to its own place: a worktree
   (`isolation: "worktree"`) when it changes code, otherwise its own scratch directory. An isolated
   worktree starts from the default branch, so give each attempt the SHA under investigation and
   have it run `git switch -C <branch> <SHA>` before any work. Each produces
   the artifact plus a short rationale naming the alternatives it considered and rejected.
   - With agent teams enabled (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`), use named teammates.
     Research, review, and competing hypotheses are where teams do best, because teammates can
     message each other: tell hypothesis investigators to try to disprove each other's theories,
     not only to support their own. A teammate spawn cannot take `isolation`, so a teammate that
     changes code creates its own worktree first.
   - Otherwise use background subagents. They don't talk to each other; the judging step does the
     challenging.
   - A Claude Code workflow is the tool when the fan-out runs to dozens of agents, but a workflow
     you write yourself for a fan-out needs the user's explicit ask. Suggest it and wait for a yes;
     don't start one on your own.
   If an attempt fails to produce its artifact, go on with the rest and note the dropout.

4. **Judge against the rubric.** Once every attempt is in, spawn one read-only judge subagent with
   the rubric and the attempts by label; use a different model from the one that wrote them when the
   call is judgment-heavy. While it works, read every attempt end to end yourself and score each
   criterion separately, not on overall feel. Then compare with the judge. Agreement confirms the
   pick; disagreement means one of you is biased or the rubric is ambiguous, so reread both
   rationales before deciding.

5. **Pick the base.**
   - For a design: the attempt a future maintainer can extend most easily without breaking its
     invariants. When two tie, take the smaller interface or the cleaner boundary.
   - For hypotheses: the one whose prediction held under the probe and that the others failed to
     disprove. A hypothesis that only survived because nobody tested it is not a winner.
   - When the attempts converge on one shape, that agreement is the result; ship the consensus.
   - When they diverge wildly, the frame was underspecified. Tighten step 1 and run again rather than
     averaging the differences.

6. **Graft by hand.** Walk each losing attempt once more for what is worth carrying over; usually one
   or two things each, not most of it. Fold each graft into the base so the result still reads as one
   design under one mental model. Don't paste mechanically.

7. **Verify the synthesis.** The merged result gets the same scrutiny as any other work
   ([prove it works](../../canon/prove-it-works.md)): run it, test it, or rerun the probe. If
   verification finds a problem no attempt caught, the frame was wrong; if one attempt caught it and
   the graft missed it, go back to step 6.

8. **Record the result.** Post it where the decision belongs: as a ruling comment on the issue
   (Ruling / Why / Cost if wrong), naming the base, the grafts and which attempt each came from, what
   was rejected and why, and any dropouts. When the choice meets the ADR test in
   [domain docs](../spec/references/domain-docs.md), offer an ADR in `docs/adr/`. Delete the losing worktrees and scratch directories once
   the record is posted.

## Next moves

- `compost:implement` when the winning design settles a question an issue in flight was waiting on.
- `compost:slice` when the winning design needs to be cut into issues.
- `compost:diagnose` when the surviving hypothesis names a cause that now needs a root fix.
- `compost:deepen` when the attempts showed the module boundary itself is the problem.
