---
name: sdlc
description: Start (or resume) an autonomous SDLC loop — a state machine on disk driven by /goal, working without questions until DONE or BLOCKED
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Task
  - Skill
argument-hint: "<description of what to build>"
---

# Autonomous SDLC Loop — Initializer

You are not the orchestrator. You initialize (or resume) a loop, arm its driver, and
run the first iteration. The `sdlc-loop` skill holds the state machine; read it now —
every iteration of this loop follows its ritual.

The user has requested: $ARGUMENTS

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/sdlc_state.py`

## 1. Resume or initialize

```bash
python3 $STATE init --feature {slug} --request "$ARGUMENTS" \
  --max-iterations 50 --max-attempts 3
```

- Derive `{slug}` from the request ("Add user authentication" → `user-auth`).
- `init` is **idempotent**: if `.sdlc/state.json` exists it prints
  `RESUME state=... iteration=...` and changes nothing. On resume, skip to step 3 —
  do not re-plan, do not recreate branches; the disk already knows where you are.
  If resuming from `BLOCKED`, read `.sdlc/escalation.md`, apply whatever the user
  changed or answered, transition back to the appropriate active state with a reason,
  then continue.
- The driver starts as `auto`: the fallback Stop hook drives until step 2 proves
  `/goal` works and records it. You never need to guess driver availability.

## 2. Arm the loop driver

**Goal driver** — set the goal exactly like this, substituting the **absolute path** of
`${CLAUDE_PLUGIN_ROOT}/scripts/sdlc_state.py` (resolve it now — the goal evaluator
cannot expand variables or placeholders):

```
/goal The SDLC loop for {slug} is finished: `python3 /absolute/path/to/scripts/sdlc_state.py state`
prints DONE or BLOCKED, demonstrated in the transcript. Or stop after 50 turns.
```

Then **record the outcome** — this is how `auto` resolves, no version guessing:

- `/goal` was accepted (the goal is active): `python3 $STATE set-driver goal` — this
  stands the fallback Stop hook down so only the evaluator drives.
- `/goal` errored or doesn't exist (Claude Code < v2.1.139, or hooks disabled):
  `python3 $STATE set-driver stop-hook` — the plugin's `loop-stop-hook.sh` (already
  registered, and already driving while the driver is `auto`) blocks every stop and
  re-injects the iteration ritual until state is DONE or BLOCKED.

The built-in evaluator (a separate small model) re-prompts after every turn until the
state machine itself says the loop is over. Completion is judged by a model that didn't
do the work.

## 3. Run the first iteration

Follow the `sdlc-loop` skill's iteration ritual: tick → orient → one unit of work →
record → stop. Then **stop normally** — the driver decides whether the next iteration
runs. Do not try to complete multiple states in one turn.

## Rules that bind every iteration

- One unit of work per iteration; commit it before stopping.
- Decide, log (`$STATE decide`), proceed — never ask the user mid-loop. Escalation is
  `transition BLOCKED` + `.sdlc/escalation.md`, nothing else.
- If `tick` prints `DONE` or `BLOCKED`, report the final status to the user:
  feature, branch, PR URL (from `.sdlc/progress.md`) or escalation summary, iterations
  used, and the count of logged decisions.
