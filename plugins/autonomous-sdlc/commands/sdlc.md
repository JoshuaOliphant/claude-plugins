---
name: sdlc
description: Start (or resume) an autonomous SDLC loop — a state machine on disk driven by a Stop-hook loop (or a user-armed self-paced /loop), working without questions until DONE or BLOCKED
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
  --max-iterations 50 --max-attempts 3 \
  [--reviewers code-review,security-review] [--review-mode block|annotate]
```

- Derive `{slug}` from the request ("Add user authentication" → `user-auth`).
- **Review gate (optional, per-project)**: `--reviewers` is a comma-separated, ordered
  list of reviewers run at the REVIEW state; `--review-mode` is `block` (findings become
  fix tasks → BUILD) or `annotate` (findings only listed in the PR body). Omit both to
  keep the default `code-review` / `block` (current behavior). Add `security-review` for
  security-sensitive work, or pr-review-toolkit agents (`pr-test-analyzer`,
  `type-design-analyzer`, `comment-analyzer`, `silent-failure-hunter`) when that plugin
  is installed. A project that prefers a non-blocking advisory gate uses `--review-mode
  annotate`. The config is persisted in `.sdlc/state.json` and the `sdlc-loop` skill
  reads it every REVIEW iteration; it survives resume.
- `init` is **idempotent**: if `.sdlc/state.json` exists it prints
  `RESUME state=... iteration=...` and changes nothing. On resume, skip to step 3 —
  do not re-plan, do not recreate branches; the disk already knows where you are.
  If resuming from `BLOCKED`, read `.sdlc/escalation.md`, apply whatever the user
  changed or answered, transition back to the appropriate active state with a reason,
  then continue.
- The driver starts as `auto`, which means the plugin's Stop hook drives — see step 2.

## 2. The loop driver

**The Stop hook drives by default.** The plugin's `loop-stop-hook.sh` (already
registered, active while the driver is `auto` or `stop-hook`) blocks every stop and
re-injects the iteration ritual until the state is DONE or BLOCKED. There is nothing
for you to arm.

**Offer the `/loop` upgrade once, in your kickoff message** (interactive sessions only;
this is information, not a blocking question). `init` wrote `.claude/loop.md` with the
iteration ritual, so a bare `/loop` runs it **self-paced**: Claude chooses the delay
between iterations (short while work is ready, 5 to 15 minutes while builders run) and
ends the loop itself when `tick` prints DONE or BLOCKED. Print exactly:

```
/loop
```

and say that if they run it, they should tell you so you can record
`python3 $STATE set-driver loop`, which stands the Stop hook down so the two drivers
don't both re-prompt. Until they say so, assume the Stop hook drives; never wait for an
answer. `/loop` is user-invoked; you cannot start it yourself.

Headless and unattended runs need neither: `claude -p "/sdlc '<request>'"` runs under
the Stop hook, and a backgrounded interactive session keeps a `/loop` firing without a
terminal.

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
