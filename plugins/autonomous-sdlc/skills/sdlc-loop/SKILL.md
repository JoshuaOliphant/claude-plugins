---
name: sdlc-loop
description: >
  The autonomous-sdlc state machine. Loaded by every /sdlc loop iteration to decide
  what one unit of work the current state requires, how to verify it, and which
  transition to record. Trigger: an active `.sdlc/state.json` exists, or the /sdlc
  command invokes it. Not for ad-hoc use outside a loop.
version: 2.0.0
effort: high
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Task
  - Skill
---

# SDLC Loop

You are one iteration of a loop. Context from previous iterations may be gone — that is
by design. Everything you need is on disk; everything the next iteration needs must be
on disk before you stop.

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/sdlc_state.py` (run with `python3`).

## The Iteration Ritual

Every iteration, in order, no exceptions:

1. **Tick**: `python3 $STATE tick` — increments the iteration counter and enforces
   budgets. If it prints `DONE` or `BLOCKED`, stop immediately: the loop is over.
2. **Orient**: `python3 $STATE status`, read the tail of `.sdlc/progress.md`, run
   `git log --oneline -10`, and read `.sdlc/signs.md` if it exists (guardrails from
   past mistakes — they override your instincts). On your first iteration in a session,
   also load stored preferences:
   `python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc show-feedback`
   — apply `loop_behavior`, `verification`, and `general` entries.
3. **Work**: do **one unit of work** for the current state (dispatch table below).
4. **Record**: commit the work, then `python3 $STATE note-progress --what "..."` or
   `python3 $STATE transition <NEXT> --reason "..."`. A transition counts as progress;
   an iteration with neither a commit nor a transition counts toward the no-progress
   limit (2), after which the loop force-blocks.
5. **Stop.** The loop driver (the `/goal` evaluator, or the fallback Stop hook) decides
   whether another iteration runs. Never try to "finish the whole feature" in one
   iteration — small verified steps survive context loss; heroics don't.

## Dispatch Table

### INIT → SPEC
Confirm the environment: feature branch exists (create `feature/{slug}` if not), state
files committed, tooling detected (`bd`, `gh`/`glab`, test runner). Transition to SPEC.
On unfixable environment problems (no git repo, no write access): escalate.

### SPEC → PLAN
Derive acceptance criteria from `.sdlc/state.json`'s `request` field using the
`bdd-spec` skill in autonomous mode (decide-don't-ask: resolve ambiguities yourself and
log each with `$STATE decide`). Write `specs/{slug}-spec.md` with numbered AC. Commit.
Escalate **only** if the request is self-contradictory — not merely vague.

### PLAN → BUILD
If the `compound-retrieve` skill is available (compound-knowledge plugin), invoke it
first and fold past solutions and gotchas into the Architect's prompt; skip silently if
absent. Run the Architect pattern (`agents/architect.md`): plan document at
`specs/{slug}-plan.md`, tasks decomposed into Beads (`bd create` + deps) or TaskCreate.
Every AC must map to at least one task; add a doc-update task and (if the project has
user-facing surface) a docs task — there is no separate Documenter. Commit. One re-plan
is allowed (`PLAN → PLAN`); a second planning failure escalates.

### BUILD (⇄ BUILD, → VERIFY)
1. `bd ready` (or TaskList) → pick **one** task. `python3 $STATE task <id>` and
   `python3 $STATE attempt <id>` — if attempt prints `EXCEEDED`, mark the task blocked
   in the tracker, log a decision, and pick the next ready task instead.
2. Spawn a Builder (`agents/builder.md`) for the task — its TDD discipline, PostToolUse
   validators, and Stop-hook completion gate are unchanged. For 3+ *independent* ready
   tasks, spawn builders in parallel with `isolation: "worktree"` and merge their
   branches before transitioning; on Claude Code ≥ 2.1.154 a dynamic workflow may hold
   that fan-out instead. **After any merge, run the test suite before continuing** — a
   merge is a change like any other; a red post-merge suite means `transition REPAIR`.
3. Tasks remaining → stay in BUILD (`transition BUILD --reason "closed <id>, N left"`).
   No ready tasks and none in flight → `transition VERIFY`.
   All remaining tasks blocked → escalate with the list.

### VERIFY (→ REVIEW, ⇄ BUILD)
Two checks, both required:
1. **Mechanical**: the built-in **verify** skill if available, else the project's own
   stack (tests, lint, types).
2. **Spec compliance**: walk `specs/{slug}-spec.md` AC by AC and confirm each is
   demonstrably met — by its `@ac-N`-tagged test where bdd-generate scaffolding exists,
   by reading the code and exercising behavior where it doesn't. Tests passing is not
   the same as the spec being satisfied.

Both green → `transition REVIEW`. Either red → create a fix task naming the failing
check or AC, `transition BUILD`. Merge conflicts or a broken branch that isn't one
task's fault → `transition REPAIR`.

### REVIEW (→ SHIP, ⇄ BUILD)
Once per feature, not per task:
1. Built-in **code-review** skill at high effort over the branch diff (it covers
   silent-failure hunting). Apply trivial findings directly (`--fix` where supported);
   real bugs become fix tasks → `transition BUILD`.
2. If `.sdlc/state.json` was initialized with security review enabled: built-in
   **security-review** skill; findings are fix tasks → BUILD.
3. Clean (or only low-confidence notes): built-in **simplify** skill, then re-run
   VERIFY's checks — a transform is never the last step before shipping. If simplify
   broke something, revert its changes rather than debugging them.
4. Budget: after 2 REVIEW→BUILD round-trips, ship anyway and list the remaining
   low-confidence findings in the PR body. `transition SHIP`.

### SHIP → DONE
If the `compound-capture` skill is available, record any non-trivial solution or gotcha
this feature produced (once, at feature level); skip silently if absent.
Push the branch (`git push -u origin feature/{slug}`). Create the PR yourself
(`gh pr create` / `glab mr create`) with: summary from the plan doc, AC checklist from
the spec, and a **"Decisions made autonomously"** section rendered from
`.sdlc/decisions.jsonl`. Append the PR URL to `.sdlc/progress.md`. `transition DONE
--reason "<pr-url>"`. Optionally suggest the built-in **loop** skill to the user for PR
babysitting (`/loop 10m check PR CI and address review comments`). Auth failures
escalate — never store or guess credentials.

### REPAIR (→ BUILD | VERIFY)
The branch is broken in a way no single task owns. Diagnose; fix forward if the cause
is clear, otherwise `git revert` the offending commit (log the decision). Green again →
back to VERIFY (or BUILD if reverting reopened a task).

### BLOCKED (terminal)
Reached via escalation or forced by budgets. See protocol below.

## Autonomy Protocol: Decide, Log, Proceed

You do not ask the human questions mid-loop. When you hit ambiguity — naming, file
placement, an underspecified AC, conflict-resolution intent, library choice — pick the
most reasonable option by project convention and record it:

```bash
python3 $STATE decide --decision "what you chose" --why "one-line rationale"
```

The human reviews all decisions in batch in the PR. A wrong-but-logged decision costs a
review comment; a question costs the whole loop.

**Escalate only for** (the complete list):
1. Destructive or irreversible operations outside the feature branch.
2. Credentials, payments, or security boundaries you cannot cross.
3. A genuine requirements **contradiction** (mutually exclusive ACs) — not vagueness.
4. Budget exhaustion or every remaining task blocked.

Escalation procedure: write `.sdlc/escalation.md` (situation, options considered,
your recommendation), then `python3 $STATE transition BLOCKED --reason "<one line>"`.
The loop exits; the human reads one file and re-runs `/sdlc` to resume.

## Signs

When you notice the loop repeating a mistake, append a one-line guardrail to
`.sdlc/signs.md` ("Sign: don't assume X — check Y first"). Step 2 of the ritual replays
them every iteration. Durable, project-independent signs should graduate into the
`feedback` skill (`feedback save`) so future loops in other projects inherit them.
