# autonomous-sdlc v3.0.0 Slim-Down Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slim autonomous-sdlc from 10 states / 6 skills to 8 states / 5 skills — merge SPEC into PLAN and REPAIR into BUILD, retire the bdd-spec skill, and compress the sdlc-loop skill from 254 to ~150 lines — while keeping the durable spine (disk state, budgets, Stop-hook driver, completion gates) fully intact.

**Architecture:** The state machine in `sdlc_state.py` shrinks by two states with a legacy-state remap in `load()` so pre-3.0 `.sdlc/state.json` files resume cleanly. Acceptance-criteria derivation moves inline into the PLAN dispatch entry (evals showed Claude produces Given/When/Then naturally; the 173-line bdd-spec skill was non-discriminating). Broken-branch repair becomes a paragraph inside BUILD. Nothing about the Stop hook, auto-approve denylist, builder validators, or budgets changes.

**Tech Stack:** Python 3 (stdlib only in `sdlc_state.py`), pytest, markdown skill files, JSON plugin manifests.

**Rationale:** Comparison against Boris Cherny's "steps of AI adoption" levels (2026-07-18 analysis). The durable outer loop is justified — Level 3 autonomy independently re-derives it — but ~30-40% of the plugin was intelligence-compensation that Fable/Opus-class models no longer need.

## Global Constraints

- `plugins/autonomous-sdlc/.claude-plugin/plugin.json` is the version source of truth; its version must be **copied** into `.claude-plugin/marketplace.json`'s autonomous-sdlc entry. Do NOT bump `metadata.version` (no plugin added/removed).
- New version everywhere: **3.0.0** (breaking: two states removed, one skill removed).
- All Python files start with two `# ABOUTME: ` comment lines.
- Never remove code comments unless provably false; update comments that become false (there are two: see Task 1 Step 3 and Task 1 Step 5).
- Conventional commits, imperative mood, present tense.
- No "v2"/"new"/"improved" naming — evergreen names only.
- Match surrounding style in every file edited.
- Test suite must be run from `plugins/autonomous-sdlc/scripts/`: `python3 -m pytest test_sdlc_state.py -v` (fallback: `python3 test_sdlc_state.py`).
- CLAUDE.md sync rule: when an agent's role or the state machine changes, `README.md` and the `sdlc-loop` dispatch table must be updated in the same change.
- **Deliberately out of scope** (do not touch): `hooks/scripts/loop-stop-hook.sh` and `auto-approve.sh` (they reference only INIT/BUILD/DONE/BLOCKED, all of which survive; auto-approve changes are security-adjacent and need La Boeuf's separate call), `docs/sdlc-loop-redesign.md` beyond the one-line note in Task 4, `logs/*.json` sample artifacts, `evals/bdd-generate-eval.json` (its query text mentioning "/bdd-spec" is a plausible historical user utterance in a trigger-eval fixture; rewording would silently shift eval semantics), `skills/verification-stack-workspace/` and `evals/verification-stack-eval.json` (orphans from the v1 skill deleted in 2.0.0 — same cleanup class but unrelated to this task; file a Beads issue instead, Task 5 Step 5).

## Destructive Steps Notice

Task 3 deletes `plugins/autonomous-sdlc/skills/bdd-spec/` (4 files), `plugins/autonomous-sdlc/skills/bdd-spec-workspace/` (eval-run artifacts), and `evals/bdd-spec-eval.json`. All are in git history and recoverable. Executing this plan is the authorization for exactly these deletions; delete nothing else.

## Known Bug Found During Planning (fix included as Task 6)

The plugin's `WorktreeCreate` hook (`hooks/scripts/worktree-create.sh`) prints a `{"systemMessage": ...}` JSON to stdout. The Claude Code harness interprets a `WorktreeCreate` hook's stdout as a custom worktree **path**, so with this plugin installed, `EnterWorktree` fails with `ENOENT: chdir ... -> '.../{"systemMessage": ...}'`. Reproduced 2026-07-18 in this repo. The same risk applies to `worktree-remove.sh`.

## File Structure

| File | Action | Responsibility after change |
|---|---|---|
| `plugins/autonomous-sdlc/scripts/sdlc_state.py` | Modify | 8-state machine + `LEGACY_STATES` remap in `load()` |
| `plugins/autonomous-sdlc/scripts/test_sdlc_state.py` | Modify | + 5 tests for the v3 shape and legacy remap |
| `plugins/autonomous-sdlc/skills/sdlc-loop/SKILL.md` | Rewrite | Compressed dispatch table (6 active states), AC derivation inline in PLAN, broken-branch repair inline in BUILD |
| `plugins/autonomous-sdlc/skills/sdlc-loop/references/edge-case-checklist.md` | Move (from bdd-spec) | Edge-case probing used by PLAN |
| `plugins/autonomous-sdlc/skills/bdd-spec/` | Delete | — |
| `plugins/autonomous-sdlc/skills/bdd-spec-workspace/` | Delete | — |
| `plugins/autonomous-sdlc/skills/bdd-generate/SKILL.md` | Modify | Stands alone: consumes AC from spec files/conversation/user |
| `evals/bdd-spec-eval.json` | Delete | — |
| `evals/README.md` | Modify | Drop bdd-spec row mention |
| `plugins/autonomous-sdlc/README.md` | Modify | v3 diagram, state table, skills table, version history |
| `CLAUDE.md` (repo root) | Modify | v3 states line, "5 skills" |
| `docs/sdlc-loop-redesign.md` | Modify (1 line) | Historical note pointing at v3 |
| `plugins/autonomous-sdlc/.claude-plugin/plugin.json` | Modify | version 3.0.0 |
| `.claude-plugin/marketplace.json` | Modify | autonomous-sdlc entry → 3.0.0 |
| `plugins/autonomous-sdlc/hooks/scripts/worktree-create.sh` | Modify | Log without hijacking hook stdout (remove.sh is already silent — test-pinned only) |
| `plugins/autonomous-sdlc/scripts/test_worktree_hooks.py` | Create | Pins the empty-stdout hook contract |

---

### Task 1: Merge SPEC→PLAN and REPAIR→BUILD in the state machine

**Files:**
- Modify: `plugins/autonomous-sdlc/scripts/sdlc_state.py:41-72` (states/transitions), `:109-118` (`load()`), `:230-235` (`apply_increment` docstring)
- Test: `plugins/autonomous-sdlc/scripts/test_sdlc_state.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `sdlc_state.STATES == ["INIT","PLAN","BUILD","VERIFY","REVIEW","SHIP","DONE","BLOCKED"]`; `sdlc_state.LEGACY_STATES == {"SPEC": "PLAN", "REPAIR": "BUILD"}`; `load()` returns a dict whose `"state"` is never a legacy name. Task 2's SKILL.md and Task 4's docs describe exactly this graph.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/autonomous-sdlc/scripts/test_sdlc_state.py`, after `test_resume_preserves_existing_review_block` and before the `if __name__ == "__main__":` block:

```python
# --- v3 state-machine shape: SPEC merged into PLAN, REPAIR into BUILD ---


def test_removed_states_are_gone(tmp_path):
    assert "SPEC" not in sdlc_state.STATES
    assert "REPAIR" not in sdlc_state.STATES
    for targets in sdlc_state.TRANSITIONS.values():
        assert "SPEC" not in targets
        assert "REPAIR" not in targets


def test_init_transitions_directly_to_plan(tmp_path):
    _init(tmp_path)
    _run(tmp_path, sdlc_state.cmd_transition, target="PLAN", reason="env ready")
    assert _read_state(tmp_path)["state"] == "PLAN"


def test_legacy_spec_state_resumes_as_plan(tmp_path):
    # A pre-3.0 loop parked in SPEC must resume as PLAN and accept PLAN's edges.
    _init(tmp_path)
    s = _read_state(tmp_path)
    s["state"] = "SPEC"
    _write_state(tmp_path, s)
    _run(tmp_path, sdlc_state.cmd_transition, target="BUILD", reason="plan committed")
    assert _read_state(tmp_path)["state"] == "BUILD"


def test_legacy_repair_state_resumes_as_build(tmp_path):
    # A pre-3.0 loop parked in REPAIR must resume as BUILD and accept BUILD's edges.
    _init(tmp_path)
    s = _read_state(tmp_path)
    s["state"] = "REPAIR"
    _write_state(tmp_path, s)
    _run(tmp_path, sdlc_state.cmd_transition, target="VERIFY", reason="branch green")
    assert _read_state(tmp_path)["state"] == "VERIFY"


def test_transition_to_removed_state_is_rejected(tmp_path):
    import pytest

    _init(tmp_path)
    with pytest.raises(SystemExit):
        _run(tmp_path, sdlc_state.cmd_transition, target="REPAIR", reason="nope")
```

Also register the four non-pytest-dependent tests in the fallback runner list (the `tests = [...]` literal inside `if __name__ == "__main__":`), after `test_init_on_in_progress_does_not_increment,`:

```python
        test_removed_states_are_gone,
        test_init_transitions_directly_to_plan,
        test_legacy_spec_state_resumes_as_plan,
        test_legacy_repair_state_resumes_as_build,
```

(`test_transition_to_removed_state_is_rejected` needs pytest, so it stays out of the fallback list — same convention as `test_invalid_review_mode_is_rejected`.)

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `cd plugins/autonomous-sdlc/scripts && python3 -m pytest test_sdlc_state.py -v`
Expected: the 12 existing tests PASS; the 5 new tests FAIL (`test_removed_states_are_gone` on the SPEC assertion; `test_init_transitions_directly_to_plan` because INIT→PLAN is not a legal edge yet; the two legacy tests because SPEC/REPAIR are still real states with different edges; the rejection test because REPAIR is still a known state).

- [ ] **Step 3: Replace the state/transition tables**

In `plugins/autonomous-sdlc/scripts/sdlc_state.py`, replace lines 41-72 (from `STATES = [` through the `for _s in ACTIVE_STATES:` loop) with:

```python
STATES = [
    "INIT",
    "PLAN",
    "BUILD",
    "VERIFY",
    "REVIEW",
    "SHIP",
    "DONE",
    "BLOCKED",
]

ACTIVE_STATES = [s for s in STATES if s not in ("DONE", "BLOCKED")]

# Forward edges plus the loop's defining backward edges. BLOCKED is reachable
# from everywhere (escalation is always a legal exit).
TRANSITIONS = {
    "INIT": {"PLAN"},
    "PLAN": {"BUILD", "PLAN"},  # one re-plan allowed
    "BUILD": {"BUILD", "VERIFY"},  # one task per iteration; broken-branch repair stays here
    "VERIFY": {"BUILD", "REVIEW"},  # red → back to BUILD with a fix task
    "REVIEW": {"BUILD", "SHIP"},  # findings → back to BUILD
    "SHIP": {"DONE"},
    "DONE": set(),
    "BLOCKED": set(ACTIVE_STATES),  # human restart resumes the loop
}
for _s in ACTIVE_STATES:
    TRANSITIONS[_s] = TRANSITIONS[_s] | {"BLOCKED"}

# States removed in 3.0.0, remapped on load so pre-3.0 state files resume
# cleanly: SPEC's work (acceptance criteria) now happens inside PLAN; REPAIR's
# (broken-branch fixes) now happens inside BUILD.
LEGACY_STATES = {"SPEC": "PLAN", "REPAIR": "BUILD"}
```

Note this deliberately rewrites the old header comment ("REPAIR is reachable from every active state...") because it becomes false; the replacement comment describes the surviving invariant.

- [ ] **Step 4: Remap legacy states in `load()`**

Replace the body of `load()` (currently `sdlc_state.py:109-118`) with:

```python
def load() -> dict:
    if not STATE_FILE.exists():
        sys.exit("No .sdlc/state.json — run `sdlc_state.py init` first.")
    try:
        state = json.loads(STATE_FILE.read_text())
    except ValueError as e:
        sys.exit(
            f"CORRUPT {STATE_FILE}: {e}. Restore it from git "
            f"(git checkout -- {STATE_FILE}) or re-run init after removing it."
        )
    # Pre-3.0 state files may be parked in a removed state; remap in memory.
    # The next save() persists the mapped name.
    if state.get("state") in LEGACY_STATES:
        state["state"] = LEGACY_STATES[state["state"]]
    return state
```

- [ ] **Step 5: Fix the now-false docstring sentence in `apply_increment`**

In the `apply_increment` docstring (`sdlc_state.py:232-235`), change the sentence

`without this the only path to increment 2 is an off-graph DONE→SPEC nudge`

to

`without this the only path to increment 2 is an off-graph DONE→PLAN nudge`

(the rest of the docstring stays untouched).

- [ ] **Step 6: Run the full suite to verify green**

Run: `cd plugins/autonomous-sdlc/scripts && python3 -m pytest test_sdlc_state.py -v && python3 -m pytest test_loop_stop_hook.py -v`
Expected: all 17 tests in `test_sdlc_state.py` PASS; all of `test_loop_stop_hook.py` PASS unchanged (the hook only reads BUILD/DONE/BLOCKED, which all survive).

- [ ] **Step 7: Commit**

```bash
git add plugins/autonomous-sdlc/scripts/sdlc_state.py plugins/autonomous-sdlc/scripts/test_sdlc_state.py
git commit -m "feat(autonomous-sdlc): merge SPEC into PLAN and REPAIR into BUILD

- 10 states become 8; LEGACY_STATES remap in load() resumes pre-3.0 state files
- transition graph and comments updated; tests cover the remap and rejection"
```

---

### Task 2: Rewrite the sdlc-loop skill (254 → ~150 lines)

**Files:**
- Modify (full rewrite): `plugins/autonomous-sdlc/skills/sdlc-loop/SKILL.md`
- Create (git mv from bdd-spec): `plugins/autonomous-sdlc/skills/sdlc-loop/references/edge-case-checklist.md`

**Interfaces:**
- Consumes: the 8-state graph and `LEGACY_STATES` from Task 1 (dispatch entries must match `TRANSITIONS` exactly).
- Produces: PLAN dispatch entry that writes `specs/{slug}-spec.md` with `AC-N` Given/When/Then blocks (the format `agents/architect.md:54` and `bdd-generate`'s prerequisite guard rely on); the reference path `references/edge-case-checklist.md` relative to the skill.

- [ ] **Step 1: Move the edge-case checklist before deleting its old home**

```bash
mkdir -p plugins/autonomous-sdlc/skills/sdlc-loop/references
git mv plugins/autonomous-sdlc/skills/bdd-spec/references/edge-case-checklist.md \
       plugins/autonomous-sdlc/skills/sdlc-loop/references/edge-case-checklist.md
```

- [ ] **Step 2: Replace SKILL.md wholesale**

Overwrite `plugins/autonomous-sdlc/skills/sdlc-loop/SKILL.md` with exactly:

````markdown
---
name: sdlc-loop
description: >
  The autonomous-sdlc state machine. Loaded by every /sdlc loop iteration to decide
  what one unit of work the current state requires, how to verify it, and which
  transition to record. Trigger: an active `.sdlc/state.json` exists, or the /sdlc
  command invokes it. Not for ad-hoc use outside a loop.
version: 3.0.0
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

You are one iteration of a loop. Context from previous iterations may be gone — by
design. Everything you need is on disk; everything the next iteration needs must be on
disk before you stop.

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/sdlc_state.py` (run with `python3`).

## The Iteration Ritual

Every iteration, in order, no exceptions:

1. **Tick**: `python3 $STATE tick`. If it prints `DONE` or `BLOCKED`, stop immediately.
   If this iteration only checks on in-flight builders, use `tick --waiting` instead —
   wait checks are free, not budgeted units of work.
2. **Orient**: `python3 $STATE status`; tail `.sdlc/progress.md`; `git log --oneline -10`;
   read `.sdlc/signs.md` if it exists (guardrails from past mistakes — they override
   your instincts). First iteration of a session, also load stored preferences:
   `python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc show-feedback`.
3. **Work**: one unit of work for the current state (dispatch table below).
4. **Record**: commit, then `python3 $STATE note-progress --what "..."` or
   `python3 $STATE transition <NEXT> --reason "..."`. An iteration with neither a commit
   nor a transition counts toward the no-progress limit (2), then the loop force-blocks.
5. **Stop.** The loop driver decides whether another iteration runs. Small verified
   steps survive context loss; heroics don't.

## Dispatch Table

### INIT → PLAN
Confirm the environment: feature branch (`feature/{slug}`), state files committed,
tooling detected (`bd`, `gh`/`glab`, test runner). Unfixable problems (no git repo, no
write access) → escalate. Soft dependency: probe for an observability harness with
`bash .claude/harness/observability/status.sh --json` (file absent → none) and note the
result in `progress.md`; if there is none, the `claude-code-observability-harness` skill
is available, and the project is a long-running app or service, log a decision and carry
"set up observability harness (lite)" into PLAN as an early task. Transition to PLAN.

### PLAN (⇄ PLAN, → BUILD)
Two units of work, in order:

1. **Acceptance criteria**: derive numbered criteria (`AC-1`, `AC-2`, …) from the
   `request` in `.sdlc/state.json`, each a **Given/When/Then** block — one action per
   When, every Then observable and testable ("returns HTTP 200 with `user_id`", never
   "works correctly"). Probe failure modes with `references/edge-case-checklist.md`;
   when 3+ edge cases share a pattern, consolidate into one parameterized table.
   Decide-don't-ask: resolve ambiguities yourself and log each with `$STATE decide`;
   escalate only a genuine contradiction, never vagueness. Write
   `specs/{slug}-spec.md`, commit, `note-progress`.
2. **Plan**: if the `compound-retrieve` skill is available, fold past solutions into
   the Architect's prompt; skip silently if absent. Run the Architect
   (`agents/architect.md`): plan at `specs/{slug}-plan.md`, tasks in Beads
   (`bd create` + deps) or TaskCreate. Every AC maps to ≥1 task; documentation updates
   are a task; if the project has (or INIT queued) an observability harness, add a
   feature-scoped instrumentation task. Commit, `transition BUILD`. One re-plan is
   allowed (PLAN → PLAN); a second planning failure escalates.

### BUILD (⇄ BUILD, → VERIFY)
1. `bd ready` (or TaskList) → pick **one** task (or several independent ones for
   parallel builders). For each: `python3 $STATE task <id>` (and `task <id> --done`
   when it closes), plus `python3 $STATE attempt <id>` — on `EXCEEDED`, mark the task
   blocked in the tracker, log a decision, pick the next ready task.
2. Spawn a Builder (`agents/builder.md`) per task — its TDD discipline, PostToolUse
   validators, and Stop-hook completion gate are unchanged. For 3+ independent ready
   tasks, spawn parallel builders with `isolation: "worktree"` and merge their branches
   before transitioning. **After any merge, run the test suite** — red after a merge is
   a broken branch (below).
3. Tasks remaining → `transition BUILD --reason "closed <id>, N left"`. None ready and
   none in flight → `transition VERIFY`. All remaining tasks blocked → escalate with
   the list.

**Broken branch** (merge conflicts, a regression no single task owns): diagnose — with
an observability harness, query recent error logs and failed spans
(`observability-query`) before reading code. Fix forward if the cause is clear,
otherwise `git revert` the offending commit (log the decision). The repair is this
iteration's unit of work; stay in BUILD.

**Waiting on builders.** Background builders take minutes; re-prompts arrive in
seconds. When builders are in flight and nothing else is ready:

1. `python3 $STATE tick --waiting` (free; bounded by its own `max_wait_ticks` ceiling).
2. **Default: block in-turn, don't hand control back.** Hold the turn open with the
   Monitor tool (or, without Monitor, a bounded
   `until [ -f <expected-output> ]; do :; done` bash wait) on the artifact the builder
   commits. A held-open turn costs no tokens while it waits; a re-prompted turn reloads
   this whole skill and re-orients.
3. If you do stop: the Stop hook is wait-aware — in BUILD with builders in flight it
   allows the stop, and the builder's completion notification re-enters the loop once.
4. When a builder finishes: `python3 $STATE task <id> --done`, verify its work, and
   take a normal work tick for whatever you do with it.

### VERIFY (→ REVIEW, ⇄ BUILD)
Required checks:
1. **Mechanical**: the built-in **verify** skill if available, else the project's own
   stack (tests, lint, types).
2. **Spec compliance**: walk `specs/{slug}-spec.md` AC by AC — each demonstrably met,
   by its `@ac-N`-tagged test where bdd-generate scaffolding exists, by exercising the
   behavior where it doesn't. Tests passing is not the same as the spec being satisfied.
3. **Telemetry** (only when the project has an observability harness): exercise the
   feature once for real and confirm the instrumented paths fired
   (`observability-query`). If the sinks look dry, run the harness `verify.sh` first —
   distinguish "pipeline broken" from "code path never executed".

All green → `transition REVIEW`. Any red → create a fix task naming the failing check
or AC, `transition BUILD`.

### REVIEW (→ SHIP, ⇄ BUILD)
Once per feature, not per task. Read the per-project gate config first:

```bash
python3 -c "import json;r=json.load(open('.sdlc/state.json')).get('review',{'reviewers':['code-review'],'mode':'block'});print(r['mode']);[print(x) for x in r['reviewers']]"
```

1. Run each entry in `reviewers` in order over the branch diff: `code-review` → the
   built-in skill at high effort (apply trivial findings via `--fix` where supported);
   `security-review` → the built-in skill; any other name (`pr-test-analyzer`,
   `type-design-analyzer`, `comment-analyzer`, `silent-failure-hunter`) → the matching
   `pr-review-toolkit` agent if that plugin is installed, else skip with a logged
   decision.
2. Handle findings per `mode`: **block** (default) — real bugs become fix tasks →
   `transition BUILD`; **annotate** — collect every finding into a "Review findings
   (annotate mode)" block for the PR body and continue.
3. Clean (or annotate mode): built-in **simplify** skill, then re-run VERIFY's checks —
   a transform is never the last step before shipping. If simplify broke something,
   revert its changes rather than debugging them.
4. Budget (block mode): after 2 REVIEW→BUILD round-trips, ship anyway and list the
   remaining low-confidence findings in the PR body. `transition SHIP`.

### SHIP → DONE
If the `compound-capture` skill is available, record any non-trivial solution or gotcha
(once, at feature level); skip silently if absent. Push the branch
(`git push -u origin feature/{slug}`). Create the PR yourself (`gh pr create` /
`glab mr create`) with: summary from the plan doc, the AC checklist from the spec, and
a **"Decisions made autonomously"** section rendered from `.sdlc/decisions.jsonl`.
Append the PR URL to `.sdlc/progress.md`. `transition DONE --reason "<pr-url>"`.
Optionally suggest the built-in **loop** skill for PR babysitting
(`/loop 10m check PR CI and address review comments`). Auth failures escalate — never
store or guess credentials.

### BLOCKED (terminal)
Reached via escalation or forced by budgets. See protocol below.

## Autonomy Protocol: Decide, Log, Proceed

You do not ask the human questions mid-loop. On ambiguity — naming, file placement, an
underspecified AC, a library choice — pick the most reasonable option by project
convention and record it:

```bash
python3 $STATE decide --decision "what you chose" --why "one-line rationale"
```

**This supersedes default caution gates, for this scope only.** Running `/sdlc` is the
user's standing, up-front authorization for the loop's routine work on
`feature/{slug}` — including editing or rewriting existing code and changing business
logic when a task calls for it, committing, and pushing the feature branch — without
per-action confirmation. A user's CLAUDE.md that lists those among "ask first" actions
is targeting *unscoped* work; explicitly invoking `/sdlc` with a request is the
pre-approval. It does **not** extend to `main`/`master`, force-pushes, history
rewrites, credentials, or the Escalate list below — those stay gated exactly as
CLAUDE.md specifies, and always route through `transition BLOCKED`, never a question.

**Prefer documented facts over guessed ones.** When a decision turns on externally
checkable behavior — a library's API, a framework's defaults, a version's breaking
changes — check current docs before logging it: `compound-retrieve` (if installed) for
past in-house solutions; the `read-the-damn-docs` skill, the `context7` MCP, or a web
search for third-party docs. Cite the source in the `--why`
(e.g. `--why "httpx 0.27 timeout default is 5s per docs"`). Skip this for pure
project-convention choices; don't stall a loop hunting for docs that don't exist.

**Budgets are adjustable, not sacred.** A legitimate loop about to exhaust a budget for
structural reasons → `python3 $STATE set-budget --max-iterations N` plus a logged
decision. Never hand-edit `state.json`.

**Escalate only for** (the complete list):
1. Destructive or irreversible operations outside the feature branch.
2. Credentials, payments, or security boundaries you cannot cross.
3. A genuine requirements **contradiction** (mutually exclusive ACs) — not vagueness.
4. Budget exhaustion or every remaining task blocked.

Escalation procedure: write `.sdlc/escalation.md` (situation, options considered, your
recommendation), then `python3 $STATE transition BLOCKED --reason "<one line>"`. The
loop exits; the human reads one file and re-runs `/sdlc` to resume.

## Signs

When the loop repeats a mistake, append a one-line guardrail to `.sdlc/signs.md`
("Sign: don't assume X — check Y first"). Step 2 of the ritual replays them every
iteration. Durable, project-independent signs graduate into the `feedback` skill
(`feedback save`) so future loops in other projects inherit them.
````

- [ ] **Step 3: Verify internal consistency**

Run: `grep -n -e 'SPEC' -e 'REPAIR' -e 'bdd-spec' plugins/autonomous-sdlc/skills/sdlc-loop/SKILL.md`
Expected: no output (exit 1). Also run `grep -c '' plugins/autonomous-sdlc/skills/sdlc-loop/SKILL.md` — expected ≈150-160 lines.

- [ ] **Step 4: Commit**

```bash
git add plugins/autonomous-sdlc/skills/sdlc-loop
git commit -m "refactor(autonomous-sdlc): compress sdlc-loop skill to the v3 dispatch table

- AC derivation inlined into PLAN; broken-branch repair inlined into BUILD
- edge-case-checklist.md moves from bdd-spec into sdlc-loop/references"
```

(Note: the `git mv` from Step 1 is committed here; the rest of bdd-spec is deleted in Task 3.)

---

### Task 3: Retire the bdd-spec skill

**Files:**
- Delete: `plugins/autonomous-sdlc/skills/bdd-spec/` (SKILL.md, `evals/evals.json`, `references/bdd-glossary.md` — `edge-case-checklist.md` already moved in Task 2)
- Delete: `plugins/autonomous-sdlc/skills/bdd-spec-workspace/`
- Delete: `evals/bdd-spec-eval.json`
- Modify: `plugins/autonomous-sdlc/skills/bdd-generate/SKILL.md:3-8,34,40-46`
- Modify: `evals/README.md:22`

**Interfaces:**
- Consumes: Task 2 already moved `edge-case-checklist.md` out (do not delete bdd-spec before Task 2's Step 1 has run).
- Produces: a bdd-generate skill whose prerequisite guard no longer names a skill that doesn't exist.

- [ ] **Step 1: Delete the skill, its workspace, and its repo-level eval**

```bash
git rm -r plugins/autonomous-sdlc/skills/bdd-spec plugins/autonomous-sdlc/skills/bdd-spec-workspace
git rm evals/bdd-spec-eval.json
```

- [ ] **Step 2: Update bdd-generate's description frontmatter**

In `plugins/autonomous-sdlc/skills/bdd-generate/SKILL.md`, replace the description (lines 3-8):

```yaml
description: >
  Use when acceptance criteria already exist — from the sdlc-loop PLAN state, a spec/plan document,
  or the user — and they need pytest-bdd scaffolding. MUST NOT run without existing acceptance
  criteria — derive numbered AC-N Given/When/Then blocks first if none exist. Trigger: "generate
  feature files", "scaffold BDD tests", "wire up pytest-bdd", "make these criteria runnable",
  "create step definitions". This is mechanical code generation, not spec writing.
```

Bump its `version:` from `1.0.0` to `1.1.0`.

- [ ] **Step 3: Update bdd-generate's body references**

Line 34, replace:
`- **Acceptance criteria** — Input from \`bdd-spec\` output, a plan document, or directly from the user`
with:
`- **Acceptance criteria** — Input from a spec document (\`specs/{slug}-spec.md\`), a plan document, or directly from the user`

Line 42, replace:
`1. \`bdd-spec\` output in the current conversation (structured AC blocks)`
with:
`1. Structured AC blocks in the current conversation`

Line 46, replace the trailing suggestion sentence:
`Suggest: "Run \`bdd-spec\` to co-author acceptance criteria first."`
with:
`Suggest: "Derive acceptance criteria first — numbered AC-N blocks, each Given/When/Then with a verifiable Then."`

- [ ] **Step 4: Update the evals index**

In `evals/README.md` line 22, replace:
`| \`bdd-spec-eval.json\` / \`bdd-generate-eval.json\` / \`tdd-workflow-eval.json\` / \`beads-workflow-eval.json\` | autonomous-sdlc workflows |`
with:
`| \`bdd-generate-eval.json\` / \`tdd-workflow-eval.json\` / \`beads-workflow-eval.json\` | autonomous-sdlc workflows |`

- [ ] **Step 5: Verify no dangling references**

Run: `grep -rn 'bdd-spec' plugins/autonomous-sdlc/ evals/ --include='*.md' --include='*.json' --include='*.py' | grep -v -e '-workspace/' -e 'bdd-generate-eval.json' -e 'README.md'`
Expected: only hits in `plugins/autonomous-sdlc/README.md` (fixed in Task 4). The allowed remnants are the eval fixture's historical query text and version-history prose.

- [ ] **Step 6: Commit**

```bash
git add -A plugins/autonomous-sdlc/skills evals
git commit -m "refactor(autonomous-sdlc): retire bdd-spec skill

- evals showed Given/When/Then structure is non-discriminating; AC derivation
  now lives inline in the sdlc-loop PLAN state
- bdd-generate stands alone; bdd-spec eval fixtures removed"
```

---

### Task 4: Sync the docs (plugin README, repo CLAUDE.md, redesign note)

**Files:**
- Modify: `plugins/autonomous-sdlc/README.md:26-47` (diagram + state table), `:93-95`, `:106-116` (skills table), `:130-132`, `:189+` (version history)
- Modify: `CLAUDE.md` (repo root — the SDLC Loop section and plugin inventory row)
- Modify: `docs/sdlc-loop-redesign.md` (one line under the title)

**Interfaces:**
- Consumes: the exact v3 state graph from Task 1 and skill set from Task 3.
- Produces: docs that agree with `sdlc_state.py` and the skills directory — the repo's stated sync invariant.

- [ ] **Step 1: Replace the README state diagram and table**

In `plugins/autonomous-sdlc/README.md`, replace the diagram block (lines 28-37) with:

```
                ┌──────────────◄──────────────┐
                │        (review findings)    │
 INIT ─► PLAN ─► BUILD ⇄ VERIFY ─► REVIEW ─► SHIP ─► DONE
          ↺
      (one re-plan)

 Any state ─► BLOCKED (escalation — the only exit that involves the human)
```

Replace the state table (lines 39-47) with:

```markdown
| State | One iteration does | Moves on when |
|---|---|---|
| INIT | Branch, state files, tooling detection | committed |
| PLAN | Acceptance criteria (`specs/{slug}-spec.md`, AC-N Given/When/Then) then the Architect's plan + task graph | plan committed, every AC mapped to a task |
| BUILD | **One task** via the Builder (TDD + hook gates); parallel builders with `isolation: "worktree"` when tasks are independent; broken-branch repair (fix forward or revert) happens here | `bd ready` is empty |
| VERIFY | Built-in **verify** skill / project test stack + spec compliance (AC by AC) + telemetry check when an observability harness exists | green (red → fix task → BUILD) |
| REVIEW | Built-in **code-review**, optional **security-review**, then **simplify** + re-verify | no high-confidence findings (max 2 round-trips) |
| SHIP | Push + `gh pr create` with the decision journal in the PR body | PR URL recorded |
```

- [ ] **Step 2: Fix the agents paragraph and skills table**

Line 94-95, replace:
`security-review, simplify), not agents. Merging is the REPAIR state plus native worktree isolation. PR creation is one \`gh pr create\` call.`
with:
`security-review, simplify), not agents. Merging and broken-branch repair live in BUILD, plus native worktree isolation. PR creation is one \`gh pr create\` call.`

In the skills table (lines 108-115), delete the `bdd-spec` row and update the `bdd-generate` row's purpose cell to `pytest-bdd scaffolding from existing acceptance criteria`.

Line 130-132 (state CLI summary) needs no change (subcommand list is unchanged).

Also update the observability bullet under "Composes With" (line 138-142): change `REPAIR queries error logs/spans first` to `broken-branch repair queries error logs/spans first`.

- [ ] **Step 3: Add the v3.0.0 version-history entry**

Insert at the top of `## Version History` (before `### v2.3.0`), and change the `### v2.3.0 (Current)` heading to `### v2.3.0`:

```markdown
### v3.0.0 (Current)
- **State machine slimmed 10 → 8 states**: SPEC merged into PLAN (acceptance criteria
  are PLAN's first unit of work), REPAIR merged into BUILD (broken-branch repair is a
  BUILD iteration). Pre-3.0 `.sdlc/state.json` files remap on load (`LEGACY_STATES`)
  and resume cleanly. Removed states are rejected as transition targets.
- **bdd-spec skill retired**: skill-trigger evals showed the Given/When/Then structure
  is non-discriminating — Claude produces it unprompted. The AC format (AC-N numbering,
  verifiable Thens, parameterized edge-case tables) lives inline in the sdlc-loop PLAN
  entry; the edge-case checklist moved to `sdlc-loop/references/`. bdd-generate stands
  alone and consumes AC from spec files, conversation, or the user.
- **sdlc-loop skill compressed ~40%** (254 → ~150 lines): same ritual, same dispatch
  semantics, same autonomy protocol, less prose. Motivated by comparing against
  simple task-lifecycle skills (Cherny-style levels of agentic coding): the durable
  disk-state spine earns its complexity; instruction verbosity did not.
- **WorktreeCreate hook fixed**: `worktree-create.sh` no longer prints JSON to stdout,
  which the harness interpreted as a custom worktree path and broke `EnterWorktree`
  for any session with the plugin installed. Both worktree hooks' empty-stdout
  contract is now test-pinned.
```

- [ ] **Step 4: Update repo-root CLAUDE.md**

In the `### The SDLC Loop (autonomous-sdlc)` section, replace the sentence fragment:
`States: INIT → SPEC → PLAN → BUILD ⇄ VERIFY → REVIEW → SHIP → DONE, plus REPAIR and BLOCKED.`
with:
`States: INIT → PLAN → BUILD ⇄ VERIFY → REVIEW → SHIP → DONE, plus BLOCKED — acceptance criteria are PLAN's first unit of work, and broken-branch repair happens inside BUILD.`

In the Plugin Inventory table's autonomous-sdlc row, replace `6 skills` with `5 skills`.

- [ ] **Step 5: Add the historical note to the redesign doc**

In `docs/sdlc-loop-redesign.md`, insert directly under the title (before the Status line if present, else as the first body line):

```markdown
> **Historical note:** this doc describes the v2 design. v3.0.0 later merged SPEC into
> PLAN and REPAIR into BUILD and retired the bdd-spec skill — see the plugin README's
> version history. The rationale below (durable outer loop, state on disk, objective
> gates) is unchanged.
```

- [ ] **Step 6: Verify the sweep is complete**

Run: `grep -rn -e '\bSPEC\b' -e '\bREPAIR\b' plugins/autonomous-sdlc/README.md CLAUDE.md plugins/autonomous-sdlc/skills plugins/autonomous-sdlc/agents plugins/autonomous-sdlc/commands`
Expected: no hits outside the README version-history section (historical entries legitimately mention the old states).

- [ ] **Step 7: Commit**

```bash
git add plugins/autonomous-sdlc/README.md CLAUDE.md docs/sdlc-loop-redesign.md
git commit -m "docs(autonomous-sdlc): sync README and CLAUDE.md with the v3 state machine"
```

---

### Task 5: Version bump and repo health checks

**Files:**
- Modify: `plugins/autonomous-sdlc/.claude-plugin/plugin.json:3` (`"version": "2.3.1"` → `"version": "3.0.0"`)
- Modify: `.claude-plugin/marketplace.json` (autonomous-sdlc entry `"version": "2.3.1"` → `"3.0.0"`; `metadata.version` stays `1.0.10`)

**Interfaces:**
- Consumes: all prior tasks committed.
- Produces: a repo where `scripts/check_all.py` exits 0.

- [ ] **Step 1: Bump both versions**

Edit the two files as above. If the marketplace entry's `description` mentions bdd-spec or the removed states (check with `python3 -c "import json; m=json.load(open('.claude-plugin/marketplace.json')); print([p for p in m['plugins'] if p['name']=='autonomous-sdlc'][0])"`), update that description text to match the v3 skill set.

- [ ] **Step 2: Run the health checks**

Run: `python3 scripts/check_marketplace_versions.py && python3 scripts/sync_shared.py && python3 scripts/check_all.py`
Expected: all exit 0. (`sync_shared.py` must pass untouched — `feedback_manager.py` and the other shared artifacts are not modified by this plan.)

- [ ] **Step 3: Re-run the plugin test suites**

Run: `cd plugins/autonomous-sdlc/scripts && python3 -m pytest test_sdlc_state.py test_loop_stop_hook.py -v`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add plugins/autonomous-sdlc/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore(autonomous-sdlc): bump to 3.0.0 and sync marketplace"
```

- [ ] **Step 5: File the flagged follow-up (do not fix here)**

```bash
bd create --title="Remove verification-stack orphans (workspace + eval fixture)" \
  --description="skills/verification-stack-workspace/ and evals/verification-stack-eval.json are artifacts of the verification-stack skill deleted in autonomous-sdlc v2.0.0. Same cleanup class as the bdd-spec retirement but out of scope there per the unrelated-change rule. Also consider whether the auto-approve.sh PermissionRequest hook still earns its keep now that the builder runs bypassPermissions — security-adjacent, needs La Boeuf's call." \
  --type=task --priority=3
```

---

### Task 6: Fix the WorktreeCreate hook stdout bug

**Files:**
- Modify: `plugins/autonomous-sdlc/hooks/scripts/worktree-create.sh:3,16` (ABOUTME line + final echo)
- Test: `plugins/autonomous-sdlc/scripts/test_worktree_hooks.py` (new)

**Interfaces:**
- Consumes: nothing from other tasks (independent bugfix; included in the same version bump).
- Produces: a create hook that still logs to `.sdlc/events/hook-events.jsonl` but writes **nothing to stdout**, so the harness never mistakes log output for a worktree path. `worktree-remove.sh` already ends with a silent `exit 0` — it needs no fix, only a pinning test.

**Background:** Both hook scripts read the event as **stdin JSON** (`EVENT_JSON=$(cat)`) with `worktree_path` and `branch` fields, and log to `.sdlc/events/hook-events.jsonl` only when a `.sdlc/` directory exists (JSONL fields: `timestamp`, `hook_event`, `worktree_path`, `branch`). `worktree-create.sh` line 16 then echoes `{"systemMessage": "[WorktreeCreate] New worktree: path=... branch=..."}` to stdout. The harness treats a `WorktreeCreate` hook's stdout as the created worktree's **path** (the delegation contract for VCS-agnostic isolation), so `EnterWorktree` fails with `ENOENT: chdir ... '{"systemMessage": ...}'` — reproduced in this repo 2026-07-18.

- [ ] **Step 1: Write the failing test**

Create `plugins/autonomous-sdlc/scripts/test_worktree_hooks.py`:

```python
# ABOUTME: Tests for the WorktreeCreate/WorktreeRemove hook scripts.
# ABOUTME: The harness treats WorktreeCreate stdout as a worktree path — it must be empty.
"""Run from this directory: `python3 -m pytest test_worktree_hooks.py`."""

import json
import subprocess
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks" / "scripts"

EVENT = '{"worktree_path":"/tmp/wt","branch":"feature/x"}'


def _run_hook(script, tmp_path):
    return subprocess.run(
        ["bash", str(HOOKS / script)],
        cwd=tmp_path,
        input=EVENT,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_worktree_create_hook_emits_no_stdout(tmp_path):
    # Stdout from a WorktreeCreate hook is interpreted by the harness as the
    # worktree path; anything else breaks EnterWorktree with ENOENT.
    result = _run_hook("worktree-create.sh", tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""


def test_worktree_remove_hook_emits_no_stdout(tmp_path):
    result = _run_hook("worktree-remove.sh", tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""


def test_worktree_create_hook_still_logs_event(tmp_path):
    # Logging only happens when .sdlc/ exists in the cwd.
    (tmp_path / ".sdlc").mkdir()
    _run_hook("worktree-create.sh", tmp_path)
    log = tmp_path / ".sdlc" / "events" / "hook-events.jsonl"
    assert log.exists()
    entry = json.loads(log.read_text().splitlines()[-1])
    assert entry["hook_event"] == "WorktreeCreate"
    assert entry["worktree_path"] == "/tmp/wt"
    assert entry["branch"] == "feature/x"
```

- [ ] **Step 2: Run to verify exactly one test fails**

Run: `cd plugins/autonomous-sdlc/scripts && python3 -m pytest test_worktree_hooks.py -v`
Expected: `test_worktree_create_hook_emits_no_stdout` FAILS (stdout contains the systemMessage JSON); the remove-hook test and the logging test PASS (remove already exits silently).

- [ ] **Step 3: Fix worktree-create.sh**

Replace line 16:

```bash
echo "{\"systemMessage\": \"[WorktreeCreate] New worktree: path=$WORKTREE_PATH branch=$BRANCH\"}"
```

with:

```bash
echo "[WorktreeCreate] New worktree: path=$WORKTREE_PATH branch=$BRANCH" >&2
exit 0
```

And update the now-false ABOUTME line 3 from:

```bash
# ABOUTME: Logs worktree creation and surfaces path/branch to the lead orchestrator
```

to:

```bash
# ABOUTME: Logs worktree creation to .sdlc/events; stdout stays empty (harness reads it as a path)
```

- [ ] **Step 4: Run tests to verify green**

Run: `cd plugins/autonomous-sdlc/scripts && python3 -m pytest test_worktree_hooks.py -v`
Expected: all 3 PASS.

- [ ] **Step 5: Verify end-to-end**

Run: `printf '%s' '{"worktree_path":"/tmp/wt","branch":"b"}' | bash plugins/autonomous-sdlc/hooks/scripts/worktree-create.sh; echo "exit=$?"`
Expected: nothing on stdout, the `[WorktreeCreate] ...` line on stderr, `exit=0`. Optionally confirm `EnterWorktree` now succeeds in a session with the plugin's hooks active.

- [ ] **Step 6: Commit**

```bash
git add plugins/autonomous-sdlc/hooks/scripts/worktree-create.sh \
        plugins/autonomous-sdlc/scripts/test_worktree_hooks.py
git commit -m "fix(autonomous-sdlc): stop WorktreeCreate hook writing to stdout

The harness interprets WorktreeCreate hook stdout as the worktree path,
so the systemMessage JSON broke EnterWorktree with ENOENT. Message goes
to stderr; JSONL logging unchanged; tests pin the empty-stdout contract."
```

---

## Execution Order & Dependencies

```
Task 1 (state machine)  ─┐
                          ├─► Task 4 (docs) ─► Task 5 (versions + checks)
Task 2 (skill rewrite)  ─┤
Task 3 (retire bdd-spec)─┘        Task 6 (hook bugfix) — independent, any time before Task 5
```

Task 2 Step 1 (the `git mv`) must run before Task 3 Step 1 (the `git rm -r`). Task 5 is last so `check_all.py` gates the finished set.

## Not Doing (explicit)

- No changes to `loop-stop-hook.sh`, `auto-approve.sh`, the builder's validators, the haiku completion gate, budgets, or `.sdlc/` file layout — the durable spine stays.
- No renumbering/rewording of remaining skills (tdd-workflow, beads-workflow, feedback).
- No verification-stack orphan cleanup (Beads issue instead — Task 5 Step 5).
- No `metadata.version` bump in marketplace.json.
