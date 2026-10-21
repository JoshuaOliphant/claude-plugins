---
name: implement
description: Drives filed issues to a reviewed, draft-PR-ready branch, running build, verify, and review for each issue on its own and working independent issues in parallel. Use once issues exist - "implement this", "implement the spec", "work the issues", "build the tickets", "start on #42", "keep going until it's done", "finish while I'm away" - or to resume work on a parent issue that already has progress.
---

# Implement

Issues are a task graph, not a to-do list. At any moment some of them are unblocked; that set is the
frontier, and this skill's job is to keep it moving until every issue under the parent is built,
verified, and reviewed on one feature branch. You pick the flow from here without being led:
each issue goes through `compost:build`, `compost:verify`, and `compost:review`, and you decide
everything a reasonable colleague would decide, writing each ruling down on the issue instead of
stopping to ask.

Keep the orchestration light. A plain agent working an issue lands it; ceremony around that agent
(ledgers, status files, pilot runs, verifier agents that rerun one command) costs more than it buys.
The tracker and git are the only records. Parallelism is for work that splits, never for show. Order
the work so each step can be checked before the next builds on it
([sequence verifiable units](../../canon/sequence-verifiable-units.md)).

## Steps

1. **Orient.** Read `docs/agents/issue-tracker.md` for the tracker and its commands; if it is absent,
   run `compost:setup` now, then continue. If `docs/agents/observability.md` is absent, run
   `compost:setup`'s observability step on this branch before any worker branches from it. Read
   the parent issue, every sub-issue, and every comment on them: earlier rulings bind you, and a
   status comment from `compost:pause` means you are resuming, so start from its next action. Read
   `CONTEXT.md` and the ADRs in `docs/adr/` for the areas the issues touch. Run `git log` and `git worktree list` to see what already landed.

2. **Compute the frontier.** An issue is on the frontier when it is open and every issue named in its
   "Blocked by #n" lines is done. Compare the Files blocks of the frontier issues: issues whose file
   sets don't overlap can run at once; issues that share a file go into one lane and run in order.
   How many issues you take on at once is your judgment; there is no size rule.

3. **Set up the feature branch.** Work in a worktree on a feature branch named for the parent
   issue; if you are already in one, use it. Open a draft PR only when the tracker closes work
   through PRs (its reference in `docs/agents/issue-tracker.md` says an issue closes when its pull
   request merges) or the user asks for one. That PR waits until the first issue lands on the
   branch (step 5), because the forge rejects a PR with no commits over its base. Committing,
   pushing this branch, and opening the draft PR need no one's OK; merging it does.

4. **Work the frontier.**
   - **One issue, or one lane, outside a lane-routing run:** do it yourself in this session. Load
     `compost:build`, then `compost:verify`. A subagent for a single issue only adds a handoff.
   - **Several independent issues or lanes:** spawn one subagent per lane in a single message, so
     the lanes run in parallel, each with `isolation: "worktree"` and in the background, without
     asking. A lane of one issue is just that issue; a worker with a longer lane works its issues
     in order. When agent teams are enabled (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`), spawn them
     as named teammates instead; a teammate spawn cannot take `isolation`, so its brief tells it to
     create its own worktree first.
   - An isolated worktree starts from the default branch, not the feature branch. Every brief names
     the feature branch's head SHA, and the worker switches to it before any work.
   - Write each brief from [references/task-brief.md](references/task-brief.md): the issue, its
     acceptance criteria, its Interfaces block, the `CONTEXT.md` terms it uses, and pointers to any
     rulings that touch it. Size the brief to the issue; a one-file change gets a paragraph.
   - Leave `model` and `effort` unset on every spawn, so each lane inherits yours, except in a
     lane-routing run. A run is one when its ask is to tier the lanes by model or to run the
     untiered control a tiered run is compared against, or when the parent's latest "Lane
     routing:" comment is not "ended". In a lane-routing run,
     [references/lane-routing.md](references/lane-routing.md) decides how every lane spawns, a
     lone lane included, and whether a leftover marker still applies.
   - Keep a rolling window, not batches: when one worker finishes, spawn whatever its landing
     unblocked right away instead of waiting for the slowest sibling.

5. **Land each finished issue.** A completion is an event to handle, not a review to do inline.
   Read the worker's short report; if it says `DONE_WITH_CONCERNS`, read the concerns first. Merge
   its branch into the feature branch with `--no-ff`, then run the suite on the feature branch; a
   merge is a change like any other. A red suite after a merge goes to `compost:diagnose`. When the
   repo's instructions want a version bump for a changed package, commit it right after the first
   landing, before the first push, so the PR's checks are green from its first run, and again
   after any later landing that first changes another package; lanes still leave versions alone. After the first landing, push the branch and, when step 3 calls for a PR,
   open a draft PR whose body closes the parent and every sub-issue ("Closes #12, closes #13").

6. **Review every issue.** Load `compost:review` for the issue's commits. It runs the
   `/compost:review-changes` workflow through subagents; you never wait to be asked. Scope it to
   the one issue: for an issue landed by a merge, pass `base` as `<merge>^1`, `head` as
   `<merge>^2`, and `issue` as its number; for one built in this session, pass `base` as the parent of
   its first commit and `head` as its last. No issue skips review for being small: the workflow
   gives a small diff its light path, one reviewer on both axes, and that is the cheap option. Take its findings through the reception protocol there: check each against the
   code, fix what holds, and rule on what doesn't.
   - Fix findings where the work was done: resume the worker that built the issue with the findings
     verbatim, or fix them yourself when you built it. Each fix is seen failing before it passes, then
     `compost:verify` runs again. A worker's fixes land on its own branch, so land it again (step 5)
     before the re-review.
   - If three rounds of fixes still leave findings open, stop the loop. Rule on each remaining
     finding (park it, or make the smallest change that unblocks dependent issues) and post the
     ruling. A loop that won't converge is a design problem, not an effort problem.

7. **Record progress.** When an issue passes review, tick it on the parent's checklist (only this
   skill ticks the parent; workers tick their own issue's AC boxes) and comment on
   the issue with its commits and the verification you ran. With no PR to close it, close the issue
   the way the tracker says; with a local tracker that is `Status: closed` and a closing note in the
   issue file. Then recompute the frontier and go back to step 4. The checklist and git log are the
   progress record; there is no other.

8. **Step sideways when the work calls for it.** A defect you can't fix on sight goes to
   `compost:diagnose`; a question about a module's shape or an interface goes to `compost:deepen`.
   Both hand back here. An issue that turns out bigger than its acceptance criteria goes to
   `compost:slice` for a follow-up issue rather than growing in place.

9. **Decide, log, proceed.** Every judgment call you make on the user's behalf (an ambiguous
   criterion, a spec conflict, a library choice, a finding you decline) is posted as a comment on the
   issue it concerns, then you keep going:

   ```markdown
   **Ruling:** what you decided
   **Why:** the reason, citing the doc or line when it rests on an external fact
   **Cost if wrong:** what it takes to undo
   ```

   Then ask Jev whether the ruling deserves an ADR: run `adr-worthy` with the ruling's fields and
   write one in `docs/adr/` only on `offer_adr` ([jev](../spec/references/jev.md)). Exit 3 means Jev
   is unavailable: apply the three tests in [domain docs](../spec/references/domain-docs.md) yourself.

   A wrong ruling costs a review comment; a stalled run costs the user's day. Stop only for:
   - merging to the default branch;
   - irreversible or outward-facing actions: force-push, history rewrites on shared branches,
     deploys, data deletion, messages that reach people;
   - approval of an architectural spec, when the work shows the approved design has to change;
   - starting a Claude Code workflow you wrote yourself (the plugin's own `/compost:review-changes`
     needs no ask).

   compost's Stop hook holds you to this list during an implement run: when your last message waits
   on the user for anything else, Jev flags it and the hook sends you back to post a ruling and
   continue. The run ends when `compost:finish` loads, and a turn that answers a message the user
   typed is attended, so waiting on them there is allowed.

   When the run repeats a mistake (a command that needs a flag, a fixture that lies, a service that
   must be up), record the gotcha with `compound-knowledge:compound-capture` if it is installed, so
   the next run starts knowing it; otherwise note it on the parent issue. A note is the lowest level
   of fix: when a check could catch the mistake instead, file an issue for that check
   ([make mistakes impossible](../../canon/make-mistakes-impossible.md)).

10. **Close out.** When the frontier is empty and every sub-issue is ticked, run `compost:verify` on
    the whole feature branch, push, and hand off through `compost:finish`, whose recap is Goal,
    Decisions, Changes, Validation, Risk. The Decisions section lists every ruling comment, each with
    its cost if wrong. A lane-routing run lists its per-lane records in Validation. Without a
    PR, report the feature branch by name, since no PR link points to it, and leave the parent
    open: `compost:finish` closes it once the branch merges. Clean up worker worktrees whose
    branches are merged into the feature branch.

For a run that outlives the session, `compost:pause` writes the checkpoint and resuming starts at
step 1.

## Next moves

- `compost:finish` when every issue is reviewed and the feature branch passes verify.
- `compost:diagnose` when a test, merge, or behavior breaks and the cause isn't obvious.
- `compost:deepen` when an issue raises a design question about a module or interface.
- `compost:fan-out` when a ruling has two or more defensible designs worth building side by side.
- `compost:pause` when the session has to stop before the frontier is empty.
