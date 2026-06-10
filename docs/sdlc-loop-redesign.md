# autonomous-sdlc v2: From Pipeline to Loop

**Status**: Proposed design (not yet implemented)
**Target**: autonomous-sdlc v2.0.0

## 1. The Problem

The current plugin (v1.2.0) describes itself as autonomous, but structurally it is a
**one-shot pipeline with a human-shaped hole in the middle**:

1. **Terminal phases, no re-entry.** Orient → Plan → Decompose → Build → Verify →
   Integrate → Document → Ship runs front-to-back. Architect runs once; Documenter and
   PR-Creator are terminal. If the review gate finds a bug after Document, there is no
   defined path back to Build — the lead improvises or stops.
2. **The lead is the loop, and the lead is mortal.** Wave transitions (`bd ready` → spawn
   wave → wait → repeat) live in the lead's conversation context. The `TaskCompleted` /
   `TeammateIdle` hooks *surface* events but never *advance* anything. When context
   compacts or the session dies, the loop dies with it — `PostCompact` re-injecting Beads
   is a patch on this, not a fix.
3. **No convergence criteria.** Nothing defines "keep going until X is objectively true."
   The only hard gate is the Builder's Stop hook. Everything above task level is
   judgment-calls-in-context.
4. **Redundant machinery.** `verification-stack` re-implements the built-in `/verify`
   skill. The optional Refine/Review-Gate phases depend on a third-party
   `pr-review-toolkit` when Claude Code now ships `/code-review` (with `--fix`),
   `/simplify`, `/security-review`, and `/loop` as built-ins.
5. **Asks instead of decides.** Agents are told to "message the lead" or wait for the
   user at several points (bdd-spec's confirmation checkpoint, integrator ambiguity,
   lead mode-selection). Each one is an exit from autonomy.

## 2. What the Research Says

> **Origin note**: this redesign was prompted by the video
> ["How the Top 1% Actually Run Claude Code Now"](https://www.youtube.com/watch?v=2-0lxK2wgJ8),
> whose thesis matches the philosophy attributed to the Head of Claude Code: *"I don't
> prompt Claude anymore. I have loops running. They're the ones prompting Claude...
> My job is to write loops."* The pipeline-vs-loop framing below follows from that.

Four converging bodies of practice informed this design:

**The Ralph Wiggum loop** (Geoffrey Huntley; now an official plugin in
`anthropics/claude-code`): a dumb `while true` that re-feeds one prompt beats clever
orchestration. Its load-bearing ideas:
- **One task per iteration**, then restart with fresh context. Memory lives in files and
  git, not in the conversation.
- **Completion is a string match** (`<promise>COMPLETE</promise>`) plus a
  `--max-iterations` ceiling — objective exit, bounded cost.
- **Backpressure beats direction**: don't write longer prompts; engineer an environment
  (tests, types, lint, hooks) that automatically rejects wrong output.
- **Signs**: guardrail lines added to the prompt after watching the agent make a specific
  mistake ("check whether the helper exists before writing it").
- Mechanically in Claude Code it's a **Stop hook that blocks exit** and re-injects the
  prompt until the promise string appears.

**Anthropic's long-running-agent harness** (engineering blog, "Effective harnesses for
long-running agents"): split the work into an **initializer agent** (sets up environment,
feature list, progress file, initial commit) and a **coding agent** that runs every
subsequent session; every session starts with the same orientation ritual (read progress
file + git log), works on **one feature at a time**, verifies, commits, and leaves
structured notes for the next session. The insight: design for the *next* context window,
not the current one.

**Gas Town / Beads** (Steve Yegge): agents have no memory between sessions — the "50
First Dates" problem — so the issue tracker *is* the orchestrator's memory. Persistent
state in git (`.beads/*.jsonl`), ephemeral workers ("polecats") that spawn, do one task,
and disappear, and a merge-queue role. Also a widely-echoed warning (Chris Parsons,
"Your Agent Orchestrator Is Too Clever"): orchestration logic that lives in an LLM's
context is the first thing to break; keep the control loop dumb and external, keep the
intelligence inside the iterations.

**Claude Code's native loop primitives** (docs: [`/goal`](https://code.claude.com/docs/en/goal),
[workflows](https://code.claude.com/docs/en/workflows)): the harness now ships the loop
machinery itself.
- **`/goal <condition>`** (v2.1.139+) keeps a session working until a condition holds.
  It is documented as *"a wrapper around a session-scoped prompt-based Stop hook"*: after
  every turn a small fast model (Haiku) judges the condition against the transcript;
  "no" re-prompts Claude with the reason, "yes" ends the loop. Conditions support
  in-condition budgets ("or stop after 20 turns"), survive `--resume`, and run headless
  via `claude -p "/goal ..."`. This is *exactly* the Ralph mechanism, productized.
- **`/loop`** re-runs a prompt on a clock — progress-driven vs time-driven: `/goal`
  pushes work to a finish line; `/loop` watches for change.
- **Dynamic workflows** (v2.1.154+): Claude writes a JavaScript orchestration script the
  runtime executes in the background — the script holds the loop and intermediate state,
  not the context window; resumable; **no mid-run user input by design**; up to 1000
  agents/run. The docs explicitly invite porting hand-built orchestrators to workflows.

The common shape: **a dumb, durable outer loop; smart, ephemeral inner work; all state on
disk; objective gates between states.** And critically for this plugin: the outer loop no
longer needs to be hand-built.

## 3. Design Overview

Replace the eight-phase pipeline with a **state machine on disk, driven by a Stop-hook
loop**, with smaller convergence loops nested inside each state.

```
                 ┌──────────────────────────────────────────────┐
                 │  OUTER LOOP (Stop hook re-entry, budgeted)   │
                 │                                              │
   /sdlc ──────► │  read .sdlc/state.json ──► dispatch on state │
                 │        ▲                          │          │
                 │        └── commit + update state ◄┘          │
                 └──────────────────────────────────────────────┘

   States:
                       ┌────────────◄────────────┐
                       │      (review findings)  │
   INIT ─► SPEC ─► PLAN ─► BUILD ⇄ VERIFY ─► REVIEW ─► SHIP ─► DONE
                       ▲      │                  │
                       │      ▼                  ▼
                       └── REPAIR ◄───── (broken main / regression)

   Any state ─► BLOCKED (escalation: the only exit that asks the human)
```

### 3.1 The outer loop: `/goal` as the driver, Stop hook as fallback

> **Correction (post-implementation, v2.1.1):** `/goal` turned out to be a **user-only
> slash command** — Claude cannot invoke it. The shipped design therefore inverts this
> section's preference: the plugin's Stop hook is the default driver, and `/goal` is an
> optional upgrade the *user* arms (the `/sdlc` kickoff message shows the exact goal to
> run; `set-driver goal` then stands the hook down). The rest of this section's
> reasoning about the evaluator still applies when the user arms it.

`/sdlc "<request>"` no longer *is* the orchestrator. It is the **loop initializer**:

1. Create `.sdlc/state.json`, `.sdlc/progress.md`, feature branch, budgets.
2. Arm the loop by setting a **native goal**:

   ```
   /goal The SDLC state machine for feature {slug} is finished:
   `python scripts/sdlc_state.py status` prints DONE or BLOCKED,
   and the last turn committed its work. Or stop after {max_iterations} turns.
   ```

   The built-in goal evaluator (a fresh Haiku judge, separate from the model doing the
   work) then re-prompts after every turn until the condition holds — completion decided
   by a model that *didn't* do the work, which is the read-only-Validator idea reborn at
   the loop level. On Claude Code < v2.1.139 (or when hooks are disabled, which also
   disables `/goal`), the plugin falls back to its own `loop-stop-hook.sh` doing the same
   thing: on every attempted stop, read `state.json` and either:
   - state is `DONE` or `BLOCKED` → allow exit (loop ends), or
   - budget exhausted → set `BLOCKED(budget)`, allow exit, or
   - otherwise → **block the stop** and re-inject the iteration prompt.

   Headless/CI runs use the same mechanism: `claude -p "/sdlc '<request>'"` arms the
   goal and runs the loop to completion in one invocation.

Every iteration is the same short prompt (the "iteration ritual"):

> Read `.sdlc/state.json` and `.sdlc/progress.md`. Run `git log --oneline -15`.
> You are in state `{state}`. Do **one unit of work** for this state, verify it,
> commit it, update `state.json` and `progress.md`, then stop.

Because the ritual re-orients from disk every time, the loop survives compaction,
session death, and restarts. **`/sdlc` becomes idempotent**: if `.sdlc/state.json`
already exists, it resumes instead of restarting — that single property replaces most of
what `PostCompact` re-injection tries to do today.

### 3.2 The state machine

State lives in `.sdlc/state.json` (single source of truth, committed to the feature
branch so it survives anything):

```json
{
  "feature": "user-auth",
  "state": "BUILD",
  "iteration": 14,
  "budgets": { "max_iterations": 50, "max_attempts_per_task": 3 },
  "current_task": "bd-a1b2",
  "attempts": { "bd-a1b2": 1 },
  "last_progress_iteration": 13
}
```

| State | One iteration does | Exit condition (objective) | On failure |
|---|---|---|---|
| `INIT` | Branch, budgets, detect tooling (bd, gh/glab), write state files | files exist + initial commit | `BLOCKED(env)` |
| `SPEC` | Derive acceptance criteria (bdd-spec, **decide-don't-ask mode**) into `specs/{slug}-spec.md` | AC file committed | `BLOCKED(scope)` only if request is self-contradictory |
| `PLAN` | Architect pass: plan doc + task decomposition into Beads/TaskCreate | every AC maps to ≥1 task | re-enter PLAN once, then `BLOCKED` |
| `BUILD` | Pick **one** ready task, builder implements it (TDD inner loop), commit | task closed by Stop-hook gate | bump attempt counter; 3 strikes → mark task blocked, pick next; no tasks left → `BLOCKED` |
| `VERIFY` | Built-in **`/verify`** + full test run on the integrated branch | green | back to `BUILD` with a fix task (counts against budget) |
| `REVIEW` | Built-in **`/code-review`** (+ **`/security-review`** if enabled); apply findings via `--fix` or fix tasks; then **`/simplify`**; re-verify | zero high-confidence findings AND green re-verify | findings → back to `BUILD`; after 2 round-trips, ship with findings listed in PR body |
| `SHIP` | Push, open PR (one `gh pr create`, not an agent), write decision log into PR body | PR URL recorded | `BLOCKED(auth)` |
| `REPAIR` | Entered from anywhere when the branch is broken (merge conflict, red main); fix forward or revert last commit | green again | `BLOCKED` |
| `DONE` | Final progress note, clean `.sdlc/` markers (keep `decisions.jsonl` in PR) | — | — |
| `BLOCKED` | Write `.sdlc/escalation.md` (what, why, options considered, recommendation), stop loop | — | — |

Key differences from v1 phases:

- **Transitions go backward.** REVIEW findings re-enter BUILD. A regression re-enters
  REPAIR. The pipeline's "phase 7.5 found a bug, now what?" hole is gone — every state
  defines its failure transition.
- **The dispatcher is dumb.** "Read state, do one unit, write state" needs no Opus-grade
  judgment and no long-lived context. The intelligence is *inside* each iteration.
- **BUILD does one task per iteration**, Ralph-style, then the loop re-enters with
  near-fresh context. No more wave bookkeeping in the lead's head: `bd ready` *is* the
  wave. Parallelism is an optimization (spawn N builders with `isolation: "worktree"` in
  one iteration), not a different coordination mode the lead must choose upfront.

### 3.3 Inner loops (nested, budgeted)

| Inner loop | Lives in | Converges on | Budget |
|---|---|---|---|
| Red–green–refactor (existing `tdd-workflow`) | one BUILD task | task's tests green | builder Stop-hook gate (keep as-is — it already works) |
| Edit→hook-feedback (existing PostToolUse ruff/mypy hooks) | every edit | clean hooks | keep as-is |
| Verify→fix | VERIFY⇄BUILD | full stack green | counts against `max_attempts_per_task` |
| Review→fix→re-verify | REVIEW⇄BUILD | no high-confidence findings | 2 round-trips, then ship-with-notes |
| PR babysitting (post-SHIP, optional) | built-in **`/loop`** | PR merged/closed | user-configured interval |

**Progress detection** prevents spinning: if `iteration - last_progress_iteration > 2`
(no new commit, no state transition, no task closed), the Stop hook forces
`BLOCKED(no-progress)`. This is the convergence criterion the v1 design never had.

### 3.4 Reuse built-in skills; delete custom machinery

| v1 piece | v2 replacement | Action |
|---|---|---|
| `verification-stack` skill | Built-in **`/verify`** + **`/run`** | **Delete**; keep only a thin `.sdlc/verify.yaml` (project commands: test/lint/types) that `/verify` iterations read |
| Refine phase (`pr-review-toolkit:code-simplifier`) | Built-in **`/simplify`** | Replace; same green-before/re-verify-after rules |
| Review gate (`pr-review-toolkit:code-reviewer` + `silent-failure-hunter`) | Built-in **`/code-review`** at high effort (covers silent-failure hunting), optional `--fix` | Replace; drop the soft dependency entirely |
| (no security coverage) | Built-in **`/security-review`** in REVIEW before SHIP | Add (opt-in flag) |
| Lead's manual PR monitoring | Built-in **`/loop`** (e.g. `/loop 10m check PR CI and address review comments`) | Add as documented post-SHIP option |
| Custom outer-loop Stop hook | Built-in **`/goal`** (a productized session-scoped Stop hook with a separate Haiku evaluator) | Prefer; keep custom hook only as a pre-v2.1.139 fallback |
| Lead's in-context wave orchestration | **Dynamic workflows** — PLAN can emit a workflow script for large parallel BUILD waves (script holds the loop and results, not context; no mid-run user input by design) | Add as the parallelism mechanism for 6+ independent tasks |
| Plan mode alignment | Keep `plansDirectory: "specs"` recommendation | Keep |
| Worktree-manager reference | Native `isolation: "worktree"` | Already aligned; fold doc into the loop skill |

| v1 agent | v2 fate |
|---|---|
| **Architect** (Opus) | **Keep** — runs inside PLAN iterations |
| **Builder** (Opus) | **Keep** — the one-task worker; its Stop-hook completion gate is the best part of v1 |
| **Validator** (Sonnet) | **Delete** — VERIFY state runs built-in `/verify` + tests; REVIEW runs `/code-review`. The read-only-gate idea survives as *states*, not an agent |
| **Integrator** (Sonnet) | **Delete** — REPAIR state + native worktrees cover it; merge conflicts become a unit of work like any other |
| **Documenter** (Haiku) | **Delete as agent** — docs become a task type the Architect emits in PLAN (handled by Builder) |
| **PR-Creator** (Haiku) | **Delete** — SHIP is one `gh pr create` call with a template; doesn't need an agent |
| **Worktree-manager** (reference) | Fold into loop documentation |

Seven agents become two. The deleted ones weren't wrong — they were workarounds for
capabilities Claude Code didn't ship yet.

### 3.5 Autonomy policy: decide, log, proceed

The loop's contract: **a question to the human is a terminal state, not a conversation.**

1. **Decision journal instead of questions.** When an agent hits ambiguity (naming, file
   placement, interpretation of an AC, conflict-resolution intent), it picks the most
   reasonable option and appends to `.sdlc/decisions.jsonl`:
   `{"iteration": 14, "decision": "used JWT RS256 over HS256", "why": "...", "reversible": true}`.
   SHIP renders the journal into a "Decisions made autonomously" section of the PR body —
   the human reviews decisions *in batch at the end*, instead of being interrupted for
   each one. (This replaces: bdd-spec's mid-flow confirmation, integrator's
   "message the builder for intent", and the lead's mode-selection deliberation.)
2. **Escalate only for** (the entire list):
   - destructive/irreversible operations outside the feature branch (force-push, deleting
     shared data, prod-touching commands);
   - secrets, payments, or auth boundaries that require credentials the agent lacks;
   - a genuine requirements contradiction that changes scope (not ambiguity — contradiction);
   - budget exhaustion or no-progress detection.
   Escalation = write `.sdlc/escalation.md` (situation, options, recommendation), set
   `BLOCKED`, let the loop exit. The human reads one document and restarts `/sdlc`
   (which resumes from state).
3. **AskUserQuestion is removed** from every agent's toolset. The loop cannot pause on a
   question by construction, not by instruction.
4. **Backpressure over instruction.** Keep and extend the hook gates (PostToolUse
   validators, Builder Stop-hook). When the loop makes a recurring mistake, the fix is a
   new *sign* — a guardrail line in `.sdlc/signs.md`, injected into every iteration
   prompt — not a longer agent prompt. The existing `feedback` skill becomes the
   mechanism that accumulates signs and graduates durable ones into SKILL.md files
   (it already has `save`/`consolidate` — this is its natural home).

### 3.6 Safety rails

A loop that can't ask questions needs hard rails:

- `--max-iterations` (default 50) and per-task attempt caps (default 3) — Ralph's lesson:
  the ceiling, not the promise string, is the real safety mechanism.
- No-progress detection (§3.3) — two idle iterations force `BLOCKED`.
- All work confined to the feature branch; the auto-approve hook (`auto-approve-all.sh`)
  gets a **denylist** (force-push, `rm -rf` outside the worktree, package publishing,
  anything touching `main`) instead of blanket approval while `.sdlc/` exists.
- `/sdlc-status` reads `state.json` + `progress.md` (now trivially accurate);
  `/sdlc-cancel` sets state to `BLOCKED(cancelled)` so the Stop hook releases cleanly.

## 4. New File Layout

```
plugins/autonomous-sdlc/
├── agents/
│   ├── architect.md           # kept (PLAN-state worker)
│   └── builder.md             # kept (BUILD-state worker, Stop-hook gate intact)
├── commands/
│   ├── sdlc.md                # loop initializer + resumer (idempotent)
│   ├── sdlc-status.md         # renders state.json + progress.md
│   └── sdlc-cancel.md         # sets BLOCKED(cancelled)
├── skills/
│   ├── sdlc-loop/             # NEW: the state machine — dispatch table, iteration
│   │   └── SKILL.md           #      ritual, transition rules, escalation protocol
│   ├── tdd-workflow/          # kept (inner loop)
│   ├── bdd-spec/              # kept, autonomous mode default (no confirmation wait)
│   ├── bdd-generate/          # kept
│   ├── beads-workflow/        # kept (the task graph IS the loop's memory)
│   └── feedback/              # kept, extended: signs.md accumulation
├── hooks/
│   ├── hooks.json
│   ├── loop-stop-hook.sh      # NEW: fallback outer loop for Claude Code < v2.1.139
│   │                          #      (primary driver is native /goal; this replicates
│   │                          #      it: block exit unless DONE/BLOCKED, budgets,
│   │                          #      no-progress detection)
│   ├── auto-approve.sh        # tightened: denylist, branch-confinement
│   └── validators/            # kept (ruff, mypy PostToolUse)
└── scripts/
    └── sdlc_state.py          # NEW: read/transition/validate state.json (CLI, like
                               #      mochi_api.py — testable independently)
```

Deleted: `validator.md`, `integrator.md`, `documenter.md`, `pr-creator.md`,
`worktree-manager.md`, `skills/verification-stack/`, `wave-transition-check.sh`,
`post-compact.sh` (resume-from-disk obsoletes it).

## 5. Migration Plan

1. **v2.0.0-alpha** — Add `sdlc_state.py` + the `sdlc-loop` skill; rewrite `/sdlc` as
   initializer/resumer that arms a native `/goal` (with `loop-stop-hook.sh` as the
   pre-v2.1.139 fallback). Keep old agents in place (loop dispatches to them) so
   behavior is comparable.
2. **v2.0.0-beta** — Swap VERIFY/REVIEW states to built-in `/verify`, `/code-review`,
   `/simplify`, `/security-review`. Delete `verification-stack` and the
   `pr-review-toolkit` soft dependency.
3. **v2.0.0** — Delete Validator/Integrator/Documenter/PR-Creator agents; remove
   `AskUserQuestion`; tighten auto-approve denylist; update README, marketplace.json,
   and CLAUDE.md model-tiering notes (now just Architect=opus, Builder=opus).
4. Dogfood on a real feature in a sandbox repo with `max_iterations: 25` before
   publishing.

## 6. What We Deliberately Keep Simple

- **No agent-teams choreography in the core loop.** Direct teammate messaging (v1's
  agent-teams mode) is an optimization layer that can ride on top later; the research
  consistently shows the dumb loop ships more than the clever swarm. Parallel builders
  via `isolation: "worktree"` within a single BUILD iteration covers most of the win.
- **No custom completion classifier.** State transitions are checked by
  `sdlc_state.py` against objective evidence (exit codes, file existence, `bd ready`
  output, PR URL) — string-matched and scriptable, like Ralph's promise.
- **No in-context orchestration memory.** If a piece of coordination state matters, it
  goes in `state.json`, `progress.md`, Beads, or git. If it's not on disk, it doesn't
  exist.

## Sources

- [How the Top 1% Actually Run Claude Code Now (video that prompted this redesign)](https://www.youtube.com/watch?v=2-0lxK2wgJ8)
- [Claude Code docs — Keep Claude working toward a goal (`/goal`)](https://code.claude.com/docs/en/goal)
- [Claude Code docs — Orchestrate subagents at scale with dynamic workflows](https://code.claude.com/docs/en/workflows)
- [Claude Code docs — Scheduled tasks and `/loop`](https://code.claude.com/docs/en/scheduled-tasks)
- [Stop Prompting AI and Start Building Loops (on the Head of Claude Code's workflow)](https://www.productmarketfit.tech/p/stop-prompting-ai-and-start-building)
- [Ralph Wiggum plugin (official, anthropics/claude-code)](https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum)
- [Geoffrey Huntley — Ralph Wiggum as a "software engineer"](https://ghuntley.com/ralph/) and [everything is a ralph loop](https://ghuntley.com/loop/)
- [Inventing the Ralph Wiggum Loop — Dev Interrupted interview](https://devinterrupted.substack.com/p/inventing-the-ralph-wiggum-loop-creator)
- [Anthropic Engineering — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Anthropic Engineering — Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- [Steve Yegge — Gas Town / Beads (SE Daily)](https://softwareengineeringdaily.com/2026/02/12/gas-town-beads-and-the-rise-of-agentic-development-with-steve-yegge/)
- [Chris Parsons — Your Agent Orchestrator Is Too Clever](https://www.chrismdp.com/your-agent-orchestrator-is-too-clever/)
- [Mike Mason — AI Coding Agents in 2026: Coherence Through Orchestration](https://mikemason.ca/writing/ai-coding-agents-jan-2026/)
- [The Ralph Wiggum Playbook (paddo.dev)](https://paddo.dev/blog/ralph-wiggum-playbook/)
- [11 Tips For AI Coding With Ralph Wiggum (aihero.dev)](https://www.aihero.dev/tips-for-ai-coding-with-ralph-wiggum)
