# Autonomous SDLC Plugin

Autonomous software development as a **state machine on disk driven by a loop**, not a
pipeline. `/sdlc "<request>"` initializes `.sdlc/state.json`, arms a loop driver, and
then iterates — one verified, committed unit of work per turn — until the state machine
says `DONE` (PR open) or `BLOCKED` (one written escalation). No questions in between.

Design rationale: [`docs/sdlc-loop-redesign.md`](../../docs/sdlc-loop-redesign.md) in
this repository.

## Quick Start

```bash
/autonomous-sdlc:sdlc "Add user authentication with JWT tokens"   # start (or resume)
/autonomous-sdlc:sdlc-status                                      # render loop state
/autonomous-sdlc:sdlc-cancel                                      # stop cleanly (resumable)
```

Re-running `/sdlc` is always safe: if `.sdlc/state.json` exists, it resumes — including
from `BLOCKED`, after you've answered the escalation.

## The State Machine

```
                     ┌────────────◄────────────┐
                     │      (review findings)  │
 INIT ─► SPEC ─► PLAN ─► BUILD ⇄ VERIFY ─► REVIEW ─► SHIP ─► DONE
                     ▲      │                  │
                     │      ▼                  ▼
                     └── REPAIR ◄── (broken branch / regression)

 Any state ─► BLOCKED (escalation — the only exit that involves the human)
```

| State | One iteration does | Moves on when |
|---|---|---|
| INIT | Branch, state files, tooling detection | committed |
| SPEC | Acceptance criteria via `bdd-spec` (autonomous mode) | `specs/{slug}-spec.md` committed |
| BUILD | **One task** via the Builder (TDD + hook gates); parallel builders with `isolation: "worktree"` when tasks are independent | `bd ready` is empty |
| VERIFY | Built-in **verify** skill / project test stack | green (red → fix task → BUILD) |
| REVIEW | Built-in **code-review**, optional **security-review**, then **simplify** + re-verify | no high-confidence findings (max 2 round-trips) |
| SHIP | Push + `gh pr create` with the decision journal in the PR body | PR URL recorded |
| REPAIR | Fix or revert a broken branch | green again |

All state lives on disk (`.sdlc/`, git, Beads), so the loop survives context
compaction, session death, and restarts.

## Loop Drivers

- **`/goal` (preferred, Claude Code ≥ v2.1.139)**: `/sdlc` arms a goal whose condition
  is `sdlc_state.py state prints DONE or BLOCKED`. The built-in evaluator (a separate
  small model) re-prompts after every turn — completion is judged by a model that
  didn't do the work.
- **Stop hook (fallback)**: `loop-stop-hook.sh` blocks session exit and re-injects the
  iteration ritual until the state is terminal. Activates only when
  `.sdlc/state.json` has `"driver": "stop-hook"`.

Budgets guard both: max iterations (default 50), max attempts per task (default 3),
and no-progress detection (2 idle iterations force `BLOCKED`).

## Autonomy: Decide, Log, Proceed

Agents never ask questions mid-loop. Ambiguities are resolved by project convention and
logged to `.sdlc/decisions.jsonl`; SHIP renders them into a **"Decisions made
autonomously"** section of the PR for batch review. Escalation (`BLOCKED` +
`.sdlc/escalation.md`) is reserved for: destructive operations outside the feature
branch, credential/security boundaries, genuine requirement contradictions, and budget
exhaustion.

Safety rails for unattended operation:
- The permission hook **denylists** force-push, pushing/deleting `main`, hard resets to
  remote, recursive deletes outside the worktree, package publishing, and repo deletion
  — and auto-approves routine work.
- Builders cannot stop until a completion verifier confirms tests pass, code is
  committed, hooks are clean, and the task is closed.

## Agents

| Agent | Model | State | Purpose |
|-------|-------|-------|---------|
| **Architect** | Opus | PLAN | Plan document + task decomposition (docs are tasks too) |
| **Builder** | Opus | BUILD | One task with TDD; PostToolUse validators + Stop-hook completion gate |

Verification and review are **states that call built-in skills** (verify, code-review,
security-review, simplify), not agents. Merging is the REPAIR state plus native
worktree isolation. PR creation is one `gh pr create` call.

## Commands

| Command | Description |
|---------|-------------|
| `/autonomous-sdlc:sdlc <description>` | Start or resume the loop |
| `/autonomous-sdlc:sdlc-status` | Render `.sdlc/state.json` + progress |
| `/autonomous-sdlc:sdlc-cancel` | Transition to BLOCKED(cancelled); state kept for resume |
| `/autonomous-sdlc:prime` | Orient to a codebase (outside the loop) |

## Skills

| Skill | Purpose |
|-------|---------|
| `sdlc-loop` | **The state machine**: iteration ritual, dispatch table, autonomy protocol, signs |
| `bdd-spec` | Acceptance criteria — interactive with a human, decide-log-proceed inside a loop |
| `bdd-generate` | pytest-bdd scaffolding from acceptance criteria |
| `tdd-workflow` | Red-green-refactor inner loop |
| `beads-workflow` | Beads task graph — the loop's work queue (`bd ready` is the wave) |
| `feedback` | Cross-session preferences + graduation target for loop signs |

## State Files (in the target project)

```
.sdlc/
├── state.json        # single source of truth: state, iteration, budgets, attempts
├── progress.md       # append-only log every iteration orients from
├── decisions.jsonl   # autonomous decisions, rendered into the PR
├── signs.md          # guardrails accumulated from observed mistakes
└── escalation.md     # written only on BLOCKED
specs/{slug}-spec.md  # acceptance criteria
specs/{slug}-plan.md  # architect plan
```

`python3 scripts/sdlc_state.py --help` documents the state CLI (init, tick, transition,
task, attempt, decide, note-progress, status, state).

## Prerequisites

- Claude Code ≥ v2.1.139 for the `/goal` driver (older versions use the Stop-hook fallback)
- Git, `gh` or `glab` CLI, `uv` for Python projects
- Optional: Beads CLI (`bd`) for the task graph; TaskCreate is the fallback

## Recommended Settings

```json
{ "plansDirectory": "specs" }
```

Keeps Claude Code's plan mode output in the same `specs/` directory the Architect uses.

## Version History

### v2.0.0 (Current)
- **Pipeline → loop**: state machine on disk (`.sdlc/state.json`) with backward
  transitions, driven by `/goal` (Stop-hook fallback); `/sdlc` is an idempotent
  initializer/resumer
- `sdlc_state.py` state CLI: validated transitions, iteration/attempt budgets,
  no-progress detection, decision journal
- Built-in skills replace custom machinery: verify (was `verification-stack`),
  code-review + simplify + security-review (was the `pr-review-toolkit` soft
  dependency), loop for post-SHIP PR babysitting
- Agents reduced 7 → 2 (Architect, Builder); decide-log-proceed autonomy protocol;
  escalation is a terminal state with a four-item trigger list
- Auto-approve hook tightened from blanket approval to a destructive-operation denylist
- Removed wave-transition and post-compact hooks — resume-from-disk obsoletes them

### v1.4.0 and earlier
Adaptive pipeline orchestration with 7 agents, wave-based subagent processing, agent
teams mode, and the verification-stack skill. See git history for details.
