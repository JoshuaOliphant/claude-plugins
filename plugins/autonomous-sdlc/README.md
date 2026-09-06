# Autonomous SDLC Plugin

Autonomous software development as a **state machine on disk driven by a loop**, not a
pipeline. `/sdlc "<request>"` initializes `.sdlc/state.json`, writes `.claude/loop.md`, and
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
from `BLOCKED`, after you've answered the escalation. Re-running on a **finished (`DONE`)**
session with a *new* feature starts the **next increment**: the finished increment is
archived, the `cycle` counter bumps, and the loop resets to `INIT` with the new request —
so the same project can run successive features without hand-editing state. Same feature
on `DONE` is a no-op resume; a loop still mid-flight always resumes its live work.

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
| VERIFY | Project test stack (tests, lint, types) + spec compliance (AC by AC) + telemetry check when an observability harness exists | green (red → fix task → BUILD) |
| REVIEW | Built-in **code-review**, optional **security-review**, then **simplify** + re-verify | no high-confidence findings (max 2 round-trips) |
| SHIP | Push + `gh pr create` with the decision journal in the PR body | PR URL recorded |
| REPAIR | Fix or revert a broken branch | green again |

All state lives on disk (`.sdlc/`, git, Beads), so the loop survives context
compaction, session death, and restarts.

## Loop Drivers

- **Stop hook (default)**: `loop-stop-hook.sh` blocks session exit and re-injects the
  iteration ritual until the state is terminal. Drives while `.sdlc/state.json` has
  `"driver": "auto"` (the init default) or `"stop-hook"`. It is **wait-aware**: in BUILD
  with builders in flight it allows the stop and lets the completion notification
  re-enter the loop, so waiting on a multi-minute builder never spins a re-prompt per
  second. Zero-latency re-entry; works headless (`claude -p`).
- **Bare `/loop` (optional, user-armed, self-paced)**: `init` writes `.claude/loop.md`
  with the iteration ritual, which is the prompt a bare `/loop` runs. Claude then picks
  the delay between iterations itself (one minute while work is ready, 5 to 15 minutes
  while builders run) and ends the loop when `tick` prints DONE or BLOCKED. The loop
  survives `--resume` for seven days and keeps firing in a backgrounded session. `/loop`
  is user-invoked; `/sdlc`'s kickoff prints it, and if you run it, say so and Claude
  records `set-driver loop`, standing the Stop hook down. Requires Claude Code
  v2.1.248 or later on Bedrock, Foundry, or Google Cloud (self-paced `/loop` works on
  every version elsewhere).
- **`/goal`** is still accepted as a driver value for loops recorded before `/loop`
  existed, but `/sdlc` no longer offers it: the goal evaluator has no pacing, so it
  re-prompts as fast as the Stop hook without the hook's wait-awareness.

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

Verification is a state that runs the project's own test stack; review is a state
that calls built-in skills (code-review, security-review, simplify), not agents. Merging is the REPAIR state plus native
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
.claude/loop.md       # the iteration ritual a bare /loop runs (written once, never overwritten)
specs/{slug}-spec.md  # acceptance criteria
specs/{slug}-plan.md  # architect plan
```

`python3 scripts/sdlc_state.py --help` documents the state CLI (init, tick [--waiting],
transition, increment, task [--done], attempt, decide, note-progress, set-budget,
set-driver, status, state).

## Composes With (soft dependencies — skipped silently when absent)

- **compound-knowledge**: `compound-retrieve` feeds the Architect in PLAN;
  `compound-capture` records lessons before SHIP.
- **observability-harness**: INIT detects a project harness via
  `status.sh --json` (and may queue lite setup as a reviewable plan task for apps);
  PLAN adds a feature-scoped instrumentation task; VERIFY confirms the feature's
  instrumented paths actually fired (`observability-query`); REPAIR queries error
  logs/spans first.

## Prerequisites

- Optional: Claude Code ≥ v2.1.248 on Bedrock, Foundry, or Google Cloud if you want the self-paced `/loop` driver (the Stop hook needs nothing)
- Git, `gh` or `glab` CLI, `uv` for Python projects
- Optional: Beads CLI (`bd`) for the task graph; TaskCreate is the fallback

## Recommended Settings

```json
{ "plansDirectory": "specs" }
```

Keeps Claude Code's plan mode output in the same `specs/` directory the Architect uses.

## Configuring the Review Gate

The REVIEW state is configurable per-project. Two `init` flags persist into
`.sdlc/state.json` under a `"review"` block, and the `sdlc-loop` skill reads them every
REVIEW iteration:

| Flag | Values | Default | Effect |
|---|---|---|---|
| `--reviewers` | comma-separated reviewer names | `code-review` | Ordered list run at REVIEW |
| `--review-mode` | `block` \| `annotate` | `block` | Whether findings block SHIP or just annotate the PR |

```bash
# Default — equivalent to omitting both flags (preserves v2.0.0 behavior):
python3 $STATE init --feature x --reviewers code-review --review-mode block

# Security-sensitive feature, still blocking:
python3 $STATE init --feature x --reviewers code-review,security-review

# Heavier gate using pr-review-toolkit agents, advisory only:
python3 $STATE init --feature x \
  --reviewers code-review,pr-test-analyzer,type-design-analyzer \
  --review-mode annotate
```

Recognized reviewer names: `code-review` and `security-review` map to Claude Code's
built-in skills; any other name (e.g. `pr-test-analyzer`, `type-design-analyzer`,
`comment-analyzer`, `silent-failure-hunter`) is dispatched as a `pr-review-toolkit`
agent when that plugin is installed and skipped with a logged decision otherwise. In
`annotate` mode, findings are collected into the PR body and never send the loop back to
BUILD. A blank `--reviewers` value falls back to the default so the gate is never empty.

## Version History

### v2.4.0 (Current)
- **Native self-paced `/loop` replaces the `/goal` offer.** `init` writes `.claude/loop.md`
  with the iteration ritual and the state CLI's absolute path, so a bare `/loop` drives
  the loop with Claude choosing the delay between iterations (short while work is ready,
  minutes while builders run) and ending it on DONE or BLOCKED. New `loop` driver value;
  `set-driver loop` stands the Stop hook down. `goal` stays accepted for old loops.
- **No in-turn busy-waiting.** The `sdlc-loop` skill no longer holds a turn open with
  `Monitor` or a bash `until` loop while builders run: it stops, and the completion
  notification (Stop-hook driver) or the next wakeup (`/loop` driver) re-enters.
- **VERIFY no longer names the bundled `/verify` skill.** That skill is user-only
  (`disable-model-invocation`), so the loop could never call it; VERIFY runs the
  project's own test stack, as it always did in practice.
- **Worktree hooks removed.** A registered `WorktreeCreate` hook replaces git's worktree
  creation and must return `worktree_path`; the plugin's logging-only hooks broke
  `EnterWorktree` and `isolation: "worktree"`. Both hooks and their `hooks.json` entries
  are gone; nothing read the `.sdlc/events/` log they wrote.
- SHIP prints a bare `/loop` (the built-in PR-maintenance prompt) as the babysitting
  handoff instead of a custom prompt.

### v2.3.0
- **Next-increment lifecycle** (the loop is no longer single-use per project): a finished
  (`DONE`) session re-invoked with a new feature now starts increment 2 instead of silently
  resuming `DONE` and dropping the request. New `increment` subcommand archives the finished
  increment into `increments[]`, bumps a `cycle` counter, retargets `feature`/`request`, and
  resets to `INIT`; `init` auto-increments on `DONE` + new feature so a plain `/sdlc "<new>"`
  just works. Per-run loop counters (iteration, wait_ticks, attempts) reset; per-project
  config (budgets, review gate, driver) is preserved. Brings the autonomous loop to parity
  with stick-shift, which already had this. New tests cover the increment contract.
- **Soft docs-research nudge** in decide-log-proceed: the `sdlc-loop` skill and the Architect
  now *prefer* (not require) verifying externally-checkable decisions — library APIs, framework
  defaults, version changes — against current docs (`read-the-damn-docs` / `context7` / web)
  and citing the source in the decision rationale, rather than going on stale memory.

### v2.2.0
- **Wait-aware loop driver** (cuts token burn while background builders run): the Stop
  hook reads `in_flight` and, in BUILD with builders still running, **allows the stop**
  instead of re-prompting — the builder's completion notification re-enters the loop
  (one wake per completion, not one per second). The `sdlc-loop` skill now makes an
  **in-turn blocking wait** (Monitor tool) the default so the loop holds a turn open
  rather than stop-and-spin. The `>200` re-entry hard cap and `max_wait_ticks` ceiling
  remain as backstops. Backward compatible: a loop with no `in_flight` (or a pre-2.1
  `current_task`) drives exactly as before. New `test_loop_stop_hook.py` covers the
  driver's decision contract.

### v2.1.2
- **Per-project review gate**: `init --reviewers` / `--review-mode` write a `"review"`
  block to `.sdlc/state.json`; the REVIEW state reads it to choose which reviewers run
  and whether findings block SHIP (`block`) or only annotate the PR (`annotate`). Default
  (`code-review` / `block`) preserves v2.0.0 behavior exactly. Closes claude-plugins-du3.

### v2.1.1
- **Driver correction**: `/goal` is a user-only slash command — Claude cannot arm it.
  The Stop hook is now documented as the default driver; `/sdlc`'s kickoff message
  offers the exact `/goal` for the user to arm optionally (`set-driver goal` stands the
  hook down once they say they did)

### v2.1.0
- **Wait-aware budgets** (from the first field run, where ~60% of ticks were
  wait-checks on background builders): `tick --waiting` is free — separate
  `max_wait_ticks` ceiling instead of burning the iteration budget
- In-flight task **set** (`task <id>` / `task <id> --done`) replaces the single
  current-task slot, matching the parallelism the skill recommends
- `set-budget` for explicit mid-loop budget changes; `set-driver` + `--driver auto`
  (default): the Stop hook drives unless the user arms `/goal` and it's recorded
- **Observability integration** (soft dependency on `observability-harness`): harness
  detection in INIT, feature-scoped instrumentation tasks in PLAN, a telemetry check in
  VERIFY, telemetry-first diagnosis in REPAIR

### v2.0.0
- **Pipeline → loop**: state machine on disk (`.sdlc/state.json`) with backward
  transitions, driven by a Stop-hook loop (or a user-armed `/goal`); `/sdlc` is an idempotent
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
