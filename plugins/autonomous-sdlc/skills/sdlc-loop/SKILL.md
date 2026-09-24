---
name: sdlc-loop
description: >
  The autonomous-sdlc state machine. Loaded by every /sdlc loop iteration to decide
  what one unit of work the current state requires, how to verify it, and which
  transition to record. Trigger: an active `.sdlc/state.json` exists, or the /sdlc
  command invokes it. Not for ad-hoc use outside a loop.
version: 2.2.0
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
# Registered for the rest of the session when this skill is INVOKED (Skill tool
# or /sdlc); merely Reading SKILL.md registers nothing. Scoped here instead of a
# plugin-level hooks.json so the rails exist only in sessions running a loop.
# Every script no-ops unless .sdlc/state.json holds a non-terminal loop.
hooks:
  PermissionRequest:
    - matcher: ".*"
      hooks:
        - type: command
          command: bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/auto-approve.sh"
          timeout: 5
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/deny-destructive.sh"
          timeout: 5
    - matcher: "Write|Edit|MultiEdit|NotebookEdit"
      hooks:
        - type: command
          command: bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/test-lock.sh"
          timeout: 5
  Stop:
    - hooks:
        - type: command
          command: bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/loop-stop-hook.sh"
          timeout: 10
  StopFailure:
    - hooks:
        - type: command
          command: bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/stop-failure.sh"
          timeout: 10
---

# SDLC Loop

You are one iteration of a loop. Context from previous iterations may be gone — that is
by design. Everything you need is on disk; everything the next iteration needs must be
on disk before you stop.

`STATE=sdlc-state` — the plugin's `bin/` puts it on PATH while the plugin is enabled.
If `command -v sdlc-state` fails (installs distributed through claude.ai organization
settings drop `bin/`), use `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc_state.py` instead.

## Hooks this skill registers

Invoking this skill (Skill tool, or `/sdlc`, which invokes it) registers five hooks for
the rest of the session; Reading the file registers nothing, so always invoke. Each
hook stands down unless `.sdlc/state.json` holds a non-terminal loop:

- **PermissionRequest → allow** (`auto-approve.sh`): routine work never stalls on a
  prompt nobody will answer. It only allows; it never denies.
- **PreToolUse Bash → deny** (`deny-destructive.sh`): force-push, push to or delete
  `main`/`master` in any spelling (including `HEAD:main` and `refs/heads/main`),
  hard reset to remote, recursive delete of any absolute or `~` path, package
  publish, repo deletion. PreToolUse runs before permission checks in every
  mode, so this binds even for a `bypassPermissions` Builder.
- **PreToolUse Write/Edit → test-lock** (`test-lock.sh`): while a registered fix task
  is in flight, test files are read-only (see VERIFY). A green run then proves the fix.
- **Stop** (`loop-stop-hook.sh`): the default driver, re-injects the ritual.
- **StopFailure** (`stop-failure.sh`): logs API-error stops to `.sdlc/events/`.

The Builder agent carries the two PreToolUse rails in its own frontmatter as well, so
they hold inside subagents whether or not session hooks reach them.

## The Iteration Ritual

Every iteration, in order, no exceptions:

1. **Tick**: `$STATE tick` — increments the iteration counter and enforces
   budgets. If it prints `DONE` or `BLOCKED`, stop immediately: the loop is over.
   **Exception**: if this iteration exists only to check on in-flight background
   builders (no other ready work), use `$STATE tick --waiting` instead — wait
   checks are free, not budgeted units of work (see "Waiting on builders" below).
2. **Orient**: `$STATE status`, read the tail of `.sdlc/progress.md`, run
   `git log --oneline -10`, and read `.sdlc/signs.md` if it exists (guardrails from
   past mistakes — they override your instincts). On your first iteration in a session,
   also load stored preferences:
   `python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc show-feedback`
   — apply `loop_behavior`, `verification`, and `general` entries.
3. **Work**: do **one unit of work** for the current state (dispatch table below).
4. **Record**: commit the work, then `$STATE note-progress --what "..."` or
   `$STATE transition <NEXT> --reason "..."`. A transition counts as progress;
   an iteration with neither a commit nor a transition counts toward the no-progress
   limit (2), after which the loop force-blocks.
5. **Stop.** The loop driver (the plugin's Stop hook, or a user-armed self-paced
   `/loop`) decides whether another iteration runs. Never try to "finish the whole feature" in one
   iteration — small verified steps survive context loss; heroics don't.

## Dispatch Table

### INIT → SPEC
Confirm the environment: feature branch exists (create `feature/{slug}` if not), state
files committed, tooling detected (`bd`, `gh`/`glab`, test runner).

**Intent document.** `$STATE status` prints `intent: <path>`. If the file exists (the
user passed an intent doc to `/sdlc`), leave it alone. If not, write it from the
request, in the playbook's shape: title, **Pain points** (what is wrong or missing
today), **Proposed outcome** (what "done" looks like for the user), **Affected systems**
(files, services, interfaces you expect to touch, from a quick scan), and **Open
questions** (each answered inline with `$STATE decide`, never left for the human). Keep
it under a page. Commit it: it is the artifact the spec, the plan, and the PR trace
back to, and the handoff a future monitoring stage can hand *in*.

Transition to SPEC. On unfixable environment problems (no git repo, no write access):
escalate.

**Observability check (soft dependency).** Detect a project harness:
`bash .claude/harness/observability/status.sh --json` (file absent → none). Note the
result in `progress.md`. If there is **no** harness, the `claude-code-observability-harness`
skill is available, and the project is a long-running app or service (not a library or
one-shot CLI): log a decision and carry "set up observability harness (lite)" into PLAN
as an early task — it goes through normal build/verify and lands as its own reviewable
commit. Skip silently when the skill is absent or the project shape doesn't warrant it.

### SPEC → PLAN
Derive acceptance criteria from the intent document (`intent:` in `$STATE status`;
its Proposed outcome is the source of truth, the `request` string is only its seed)
using the `bdd-spec` skill in autonomous mode (decide-don't-ask: resolve ambiguities yourself and
log each with `$STATE decide`). Write `specs/{slug}-spec.md` with numbered AC. Commit.
Escalate **only** if the request is self-contradictory — not merely vague.

### PLAN → BUILD
If the `compound-retrieve` skill is available (compound-knowledge plugin), invoke it
first and fold past solutions and gotchas into the Architect's prompt; skip silently if
absent. Run the Architect pattern (`agents/architect.md`): plan document at
`specs/{slug}-plan.md`, tasks decomposed into Beads (`bd create` + deps) or TaskCreate.
Every AC must map to at least one task; add a doc-update task and (if the project has
user-facing surface) a docs task — there is no separate Documenter. If the project has
(or INIT decided to add) an observability harness, include an instrumentation task for
the feature's new surface — scan-and-propose scoped to this feature, autonomous mode —
so new code paths don't become the unobserved ones. Commit. One re-plan is allowed
(`PLAN → PLAN`); a second planning failure escalates.

**Plan gate (opt-in).** After the plan commits, run `$STATE gate plan`. It prints
`OPEN plan` unless the loop was started with `--gate plan`, in which case it writes
`.sdlc/escalation.md` ("review `specs/{slug}-plan.md`, edit in place, re-run `/sdlc`"),
moves to BLOCKED, and prints `GATED plan`: stop immediately, without transitioning.
The human's next `/sdlc` records the gate as passed and resumes in BUILD. Only on
`OPEN` do you `transition BUILD`.

### BUILD (⇄ BUILD, → VERIFY)
1. `bd ready` (or TaskList) → pick **one** task (or several independent ones for
   parallel builders). For each: `$STATE task <id>` (adds to the in-flight set;
   `task <id> --done` when it closes) and `$STATE attempt <id>` — if attempt
   prints `EXCEEDED`, mark the task blocked in the tracker, log a decision, and pick
   the next ready task instead.
2. Spawn a Builder (`agents/builder.md`) for the task — its TDD discipline, PostToolUse
   validators, and Stop-hook completion gate are unchanged. For 3+ *independent* ready
   tasks, spawn builders in parallel with `isolation: "worktree"` and merge their
   branches before transitioning; on Claude Code ≥ 2.1.154 a dynamic workflow may hold
   that fan-out instead. **After any merge, run the test suite before continuing** — a
   merge is a change like any other; a red post-merge suite means `transition REPAIR`.
3. Tasks remaining → stay in BUILD (`transition BUILD --reason "closed <id>, N left"`).
   No ready tasks and none in flight → `transition VERIFY`.
   All remaining tasks blocked → escalate with the list.

**Fix tasks** (created by VERIFY or REVIEW and registered with `$STATE fix-task <id>`)
run in the shared directory, never in a worktree: the test-lock hook reads the live
`.sdlc/state.json`, and a worktree only has the committed copy. Putting one in flight
(`$STATE task <id>`) makes every test file read-only until `task <id> --done`; the
Builder fixes source until the committed reproducing test passes. If the Builder
reports that the test itself is wrong, judge that yourself: `$STATE fix-task <id>
--unlock --reason "..."` plus a logged decision, then fix the test and re-lock by
registering again.

**Waiting on builders.** Background builders take minutes. Never busy-wait inside a
turn (no `Monitor` polls, no bash `until` loops): a held-open turn is a held-open
context. When an iteration finds builders in flight and nothing else ready:

1. `$STATE tick --waiting` (free; bounded by its own `max_wait_ticks` ceiling).
2. **Stop.** Under the Stop-hook driver, the hook allows the stop while BUILD has work
   in flight, and the builder's completion notification re-enters the loop (one wake
   per completion, not one per second). Under the `/loop` driver, schedule the next
   wakeup 5 to 15 minutes out; the completion notification may re-enter sooner.
3. When a builder finishes: `$STATE task <id> --done`, verify its work, and
   take a normal work tick for whatever you do with it.

### VERIFY (→ REVIEW, ⇄ BUILD)
Required checks:
1. **Mechanical**: the project's own stack (tests, lint, types), using the test
   command detected at INIT. (The bundled `/verify` skill is user-only and cannot be
   invoked from a loop, so never plan on it.)
2. **Spec compliance**: walk `specs/{slug}-spec.md` AC by AC and confirm each is
   demonstrably met — by its `@ac-N`-tagged test where bdd-generate scaffolding exists,
   by reading the code and exercising behavior where it doesn't. Tests passing is not
   the same as the spec being satisfied.
3. **Telemetry (only when the project has an observability harness)**: exercise the
   feature once for real and use the `observability-query` skill to confirm the
   feature's instrumented paths fired with real labels — tests can pass while the wired
   app never runs the new path. If the sinks look dry, run the harness `verify.sh`
   first: distinguish "pipeline broken" from "code path never executed" before filing
   either as a failure.

All green → `transition REVIEW`. Any red → the fix path, in this order:

1. **Reproducing test first.** If the red is an existing failing test, that is the
   reproducing test. If it is an unmet AC with no test (or a telemetry gap), write the
   failing test now, yourself, while no fix task is in flight and the test-lock is
   off. Commit it on its own ("test(ac-N): reproduce <failure>").
2. Create the fix task in the tracker naming the failing check or AC, then
   `$STATE fix-task <id>`: from the moment BUILD puts it in flight, test files are
   read-only, so the fix must make *this* test pass rather than change it.
3. `transition BUILD`.

Merge conflicts or a broken branch that isn't one task's fault → `transition REPAIR`.

### REVIEW (→ SHIP, ⇄ BUILD)
Once per feature, not per task. **Read the gate config first** — it is per-project and
lives in `.sdlc/state.json` under `"review"`:

```bash
python3 -c "import json;r=json.load(open('.sdlc/state.json')).get('review',{'reviewers':['code-review'],'mode':'block'});print(r['mode']);[print(x) for x in r['reviewers']]"
```

`reviewers` is the ordered list to run; `mode` is `block` or `annotate`. The default
(`{"reviewers": ["code-review"], "mode": "block"}`) reproduces prior behavior, so a loop
initialized without the new flags reviews exactly as before.

1. Run each entry in `reviewers` in order over the branch diff:
   - `code-review` → built-in **code-review** skill at high effort (covers
     silent-failure hunting). Apply trivial findings directly (`--fix` where supported).
   - `security-review` → built-in **security-review** skill.
   - Any other name (e.g. `pr-test-analyzer`, `type-design-analyzer`, `comment-analyzer`,
     `silent-failure-hunter`) → dispatch the matching `pr-review-toolkit` agent via the
     Task tool if that plugin is installed; skip with a logged decision if it is absent.
2. Handle findings per `mode`:
   - **block** (default): real bugs become fix tasks → `transition BUILD`, through the
     same fix path as VERIFY (reproducing test committed first, then `$STATE fix-task
     <id>`). The gate holds SHIP until the branch is clean (subject to the round-trip
     budget below).
   - **annotate**: never transition back to BUILD for findings. Collect every finding
     into a "Review findings (annotate mode)" block to paste into the PR body, then
     proceed straight to step 3.
3. Clean (or only low-confidence notes, or annotate mode): built-in **simplify** skill,
   then re-run VERIFY's checks — a transform is never the last step before shipping. If
   simplify broke something, revert its changes rather than debugging them.
4. Budget (block mode only): after 2 REVIEW→BUILD round-trips, ship anyway and list the
   remaining low-confidence findings in the PR body. `transition SHIP`.

### SHIP → DONE
If the `compound-capture` skill is available, record any non-trivial solution or gotcha
this feature produced (once, at feature level); skip silently if absent.
Push the branch (`git push -u origin feature/{slug}`). Then `$STATE gate ship`: on
`GATED ship` (the loop was started with `--gate ship`) stop immediately; the human
reviews the branch, which is already on the remote at this point (they edit locally
and push again, nothing is held back on the laptop), and their next `/sdlc` resumes
here. On `OPEN ship`, create the PR
yourself (`gh pr create` / `glab mr create`) with: summary from the plan doc, AC
checklist from the spec, a link to the intent document, and a **"Decisions made
autonomously"** section rendered from `.sdlc/decisions.jsonl`. Append the PR URL to `.sdlc/progress.md`. `transition DONE
--reason "<pr-url>"`. `transition DONE` removes `.claude/loop.md` (only the one `init`
wrote; a user's own file stays), so a bare `/loop` now falls through to Claude Code's
built-in PR-maintenance prompt. In the final report print a bare `/loop` for the user:
that prompt tends the current branch's PR (review comments, failed CI, merge conflicts)
and ends itself when the PR goes quiet. If the user armed `/loop` as the driver, its
current run ends on the next wakeup (`tick` prints DONE); they start the new one after.
On Claude Code on the web, `/autofix-pr` does the same. Auth failures escalate — never
store or guess credentials.

### REPAIR (→ BUILD | VERIFY)
The branch is broken in a way no single task owns. Diagnose — if the project has an
observability harness, the first diagnostic is the `observability-query` skill (recent
error logs and failed spans in the breakage window) before reading code. Fix forward if
the cause is clear, otherwise `git revert` the offending commit (log the decision).
Green again → back to VERIFY (or BUILD if reverting reopened a task).

### BLOCKED (terminal)
Reached via escalation or forced by budgets. See protocol below.

## Autonomy Protocol: Decide, Log, Proceed

You do not ask the human questions mid-loop. When you hit ambiguity — naming, file
placement, an underspecified AC, conflict-resolution intent, library choice — pick the
most reasonable option by project convention and record it:

**This supersedes default caution gates, for this scope only.** Running `/sdlc` is
itself the user's standing, up-front authorization for the loop's routine work on
`feature/{slug}` — including editing or rewriting existing code and changing business
logic when a task calls for it, committing, and pushing the feature branch — without
per-action confirmation. A user's own CLAUDE.md may separately list "rewriting existing
code" or "changing core business logic" among actions that normally require asking; that
default exists for *unscoped* work, where the human hasn't already pre-approved the
change. Explicitly invoking `/sdlc` with a request is the pre-approval — the same
standing-authorization pattern CLAUDE.md itself grants for git worktree lifecycle
management (one durable instruction satisfies an "ask first" gate, rather than asking
every time). It does **not** extend to `main`/`master`, force-pushes, history rewrites,
credentials, or anything on the Escalate list below — those stay gated exactly as
CLAUDE.md specifies, and always route through `transition BLOCKED`, never a question.

```bash
$STATE decide --decision "what you chose" --why "one-line rationale"
```

**Prefer documented facts over guessed ones.** When a decision turns on *externally
checkable* behavior — a library's API, a framework's defaults, a tool's flags, a version's
breaking changes — check the current docs before you log it, rather than going on memory.
`compound-retrieve` (if installed) for past in-house solutions; the `read-the-damn-docs`
skill, the `context7` MCP, or a web search for third-party/official docs. This is a strong
suggestion, not a gate — skip it for decisions that are pure project convention (naming,
file placement) and don't stall a loop hunting for docs that don't exist. When you do
verify, cite the source in the `--why` (e.g. `--why "httpx 0.27 timeout default is 5s per docs"`)
so the PR shows the decision was grounded, not guessed.

The human reviews all decisions in batch in the PR. A wrong-but-logged decision costs a
review comment; a question costs the whole loop.

**Budgets are adjustable, not sacred.** If a legitimate loop is about to exhaust a
budget for structural reasons (many parallel waves, a large plan), raise it explicitly —
`$STATE set-budget --max-iterations N` — and log the decision with the reason.
Never hand-edit `state.json` for this; the wrong key is silently ignored.

**Escalate only for** (the complete list):
1. Destructive or irreversible operations outside the feature branch.
2. Credentials, payments, or security boundaries you cannot cross.
3. A genuine requirements **contradiction** (mutually exclusive ACs) — not vagueness.
4. Budget exhaustion or every remaining task blocked.

Escalation procedure: write `.sdlc/escalation.md` (situation, options considered,
your recommendation), then `$STATE transition BLOCKED --reason "<one line>"`.
The loop exits; the human reads one file and re-runs `/sdlc` to resume.

## Signs

When you notice the loop repeating a mistake, append a one-line guardrail to
`.sdlc/signs.md` ("Sign: don't assume X — check Y first"). Step 2 of the ritual replays
them every iteration. Durable, project-independent signs should graduate into the
`feedback` skill (`feedback save`) so future loops in other projects inherit them.
