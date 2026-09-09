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
argument-hint: "<what to build, or the path to an intent.md>"
---

# Autonomous SDLC Loop — Initializer

You are not the orchestrator. You initialize (or resume) a loop, arm its driver, and
run the first iteration. The `sdlc-loop` skill holds the state machine: **invoke it now
with the Skill tool** (not Read). Invocation registers the loop's hooks for this session
(permission rails, the destructive-command denylist, the fix-task test-lock, and the
Stop-hook driver); reading the file registers nothing. Every iteration follows its ritual.

The user has requested: $ARGUMENTS

`STATE=sdlc-state` (on PATH from the plugin's `bin/`; fall back to
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc_state.py` if the command is not found).

## 1. Resume or initialize

```bash
$STATE init --feature {slug} --request "$ARGUMENTS" \
  --max-iterations 50 --max-attempts 3 \
  [--intent specs/{slug}-intent.md] [--gate plan,ship] \
  [--reviewers code-review,security-review] [--review-mode block|annotate]
```

- **Sentence or intent document.** If `$ARGUMENTS` is a path to an existing markdown
  file, it is the intent document (the playbook's `intent.md`, e.g. one written by a
  monitoring stage or a teammate): pass it as `--intent`, derive `{slug}` from its
  title, and use its first paragraph as `--request`. Otherwise derive `{slug}` from the
  sentence ("Add user authentication" → `user-auth`) and omit `--intent`: INIT writes
  `specs/{slug}-intent.md` from the request so every loop has one.
- **Approval gates (optional)**: `--gate plan` pauses after the plan commits and before
  any code is written; `--gate ship` pauses before the PR is opened. Both reuse BLOCKED
  with an escalation file that says what to review; the user's next `/sdlc` passes the
  gate. Only add a gate the user asked for (or the project's CLAUDE.md requires); the
  autonomous default has none.
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
  If `init` prints `RESUME state=... gate=<name> passed`, the human just passed an
  approval gate: continue from the printed state, nothing else to do. If resuming from
  any other `BLOCKED`, read `.sdlc/escalation.md`, apply whatever the user changed or
  answered, transition back to the appropriate active state with a reason, then continue.
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
`$STATE set-driver loop`, which stands the Stop hook down so the two drivers
don't both re-prompt. Until they say so, assume the Stop hook drives; never wait for an
answer. `/loop` is user-invoked; you cannot start it yourself.

Two footnotes for the same kickoff message, one line each: `.claude/loop.md` is
machine-local (it bakes this checkout's absolute path to the state CLI, is rewritten by
every `/sdlc`, and is removed on DONE or BLOCKED), so it belongs in `.gitignore`, not in a
commit. And self-paced `/loop` needs Claude Code v2.1.248 or later on Bedrock, Foundry,
or Google Cloud; elsewhere any version works. Skip the version line when `claude --version`
already shows 2.1.248+ or the session is not on one of those providers.

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
- If `$STATE gate` prints `GATED`, stop at once: the pause is the unit of work.
- If `tick` prints `DONE` or `BLOCKED`, report the final status to the user:
  feature, branch, PR URL (from `.sdlc/progress.md`) or escalation summary, iterations
  used, and the count of logged decisions.
