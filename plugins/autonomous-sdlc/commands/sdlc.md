---
name: sdlc
description: Start (or resume) an autonomous SDLC loop — a state machine on disk driven by a Stop-hook loop (optionally a user-armed /goal), working without questions until DONE or BLOCKED
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
- The driver starts as `auto`, which means the plugin's Stop hook drives — see step 2.

## 2. The loop driver

**The Stop hook drives by default.** `/goal` is a **user-only slash command** — you
cannot invoke it. The plugin's `loop-stop-hook.sh` (already registered, active while
the driver is `auto` or `stop-hook`) blocks every stop and re-injects the iteration
ritual until the state is DONE or BLOCKED. There is nothing for you to arm.

**Offer the /goal upgrade once, in your kickoff message** (interactive sessions only —
this is information, not a blocking question). Print the goal **ready to copy-paste**:
one fenced block, every placeholder resolved (real slug, real absolute path, the actual
max-iterations budget), nothing for the user to edit:

```
/goal The SDLC loop for {slug} is finished: `python3 {resolved absolute path to scripts/sdlc_state.py} state`
prints DONE or BLOCKED, demonstrated in the transcript. Or stop after {max_iterations} turns.
```

and that its evaluator (a separate small model judging completion — a model that didn't
do the work) then drives instead. **If the user says they armed it** (now or any time
later), run `python3 $STATE set-driver goal` to stand the Stop hook down so the two
drivers don't both re-prompt. Until they say so, assume the Stop hook drives; never
wait for an answer.

Headless runs can arm it at launch (also user-side):
`claude -p "/goal <condition as above>"` after a prior session initialized `.sdlc/`.

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
