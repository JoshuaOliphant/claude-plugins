# Stick Shift Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `stick-shift`, a manually-driven ("disassembled") SDLC plugin that shares the `.sdlc/` session format with `autonomous-sdlc` but is driven by hand via five slash commands — built for a legible, narratable 75-minute live demo.

**Architecture:** A new self-contained plugin under `plugins/stick-shift/`. A trimmed `session_state.py` owns the `.sdlc/` on-disk session (state.json, progress.md, decisions.jsonl) with only manual operations — no autonomous loop, Stop-hook, or budgets. Five thin command files (`/spec`, `/plan`, `/build`, `/verify`, `/journal`) each do exactly one phase against that session and stop, handing control back to the driver.

**Tech Stack:** Python 3 (stdlib only — `argparse`, `json`, `pathlib`, `datetime`), pytest for tests, Claude Code plugin manifest + commands. Reference (do not import): `plugins/autonomous-sdlc/scripts/sdlc_state.py` and `plugins/autonomous-sdlc/scripts/test_sdlc_state.py` for style.

**Design doc:** `docs/superpowers/specs/2026-06-20-stick-shift-design.md`

---

## File Structure

| File | Responsibility |
|---|---|
| `plugins/stick-shift/.claude-plugin/plugin.json` | Plugin manifest (name, version 0.1.0, keywords) |
| `plugins/stick-shift/scripts/session_state.py` | Manual `.sdlc/` session CLI — the only stateful code |
| `plugins/stick-shift/scripts/test_session_state.py` | Tests for the session CLI |
| `plugins/stick-shift/commands/spec.md` | Phase 1 — acceptance criteria + init |
| `plugins/stick-shift/commands/plan.md` | Phase 2 — decompose + log decisions |
| `plugins/stick-shift/commands/build.md` | Phase 3 — TDD one task |
| `plugins/stick-shift/commands/verify.md` | Phase 4 — run suite + walk criteria |
| `plugins/stick-shift/commands/journal.md` | Close — render the durable session record |
| `plugins/stick-shift/README.md` | Plugin overview + the demo rationale |
| `.claude-plugin/marketplace.json` | Register the plugin (modify) |

---

## Task 1: Scaffold the plugin

**Files:**
- Create: `plugins/stick-shift/.claude-plugin/plugin.json`
- Create: `plugins/stick-shift/README.md`

- [ ] **Step 1: Create the manifest**

Create `plugins/stick-shift/.claude-plugin/plugin.json`:

```json
{
  "name": "stick-shift",
  "version": "0.1.0",
  "description": "Manually-driven (\"disassembled\") SDLC: the same .sdlc/ session format as autonomous-sdlc, but you drive each phase by hand via slash commands — /spec → /plan → /build (TDD) → /verify → /journal. Built for legible, narratable live demos.",
  "author": {
    "name": "Joshua Oliphant",
    "email": "joshuaoliphant@gmail.com"
  },
  "keywords": [
    "sdlc",
    "tdd",
    "manual",
    "session",
    "harness",
    "developer-experience",
    "demo",
    "decision-journal"
  ],
  "repository": "https://github.com/JoshuaOliphant/claude-plugins"
}
```

- [ ] **Step 2: Create the README**

Create `plugins/stick-shift/README.md`:

```markdown
# Stick Shift

Manually-driven ("disassembled") SDLC. Same `.sdlc/` **session** format as
`autonomous-sdlc`, but you swap the autonomous Stop-hook **harness** for one you drive
by hand: five slash commands, one phase each, every one ending by handing control back
to you.

```
/spec "<task>"  →  /plan  →  /build [task]  →  /verify  →  /journal
```

| Command | Phase | Does |
|---|---|---|
| `/spec "<task>"` | SPEC (+init) | Inits `.sdlc/` + a branch; writes 3–5 Given/When/Then criteria |
| `/plan` | PLAN | Decomposes into a task list; logs key decisions |
| `/build [task]` | BUILD | TDD one task (red→green→refactor), then stops |
| `/verify` | VERIFY | Runs the suite + walks each criterion |
| `/journal` | — | Renders the durable session record |

The `.sdlc/` directory (state.json, progress.md, decisions.jsonl) is the durable
session — it survives context loss, and it is what a shared corpus (e.g.
`compound-knowledge`) would ingest. The harness is disposable; the session survives.

REVIEW is the built-in `/code-review` skill, run ad hoc. There is no SHIP — `/journal`
is the close.

## State CLI

`python3 scripts/session_state.py --help` documents the manual operations: `init`,
`state`, `status`, `transition`, `decide`, `note-progress`, `task`, `journal`.
```

- [ ] **Step 3: Commit**

```bash
git add plugins/stick-shift/.claude-plugin/plugin.json plugins/stick-shift/README.md
git commit -m "feat(stick-shift): scaffold plugin manifest and README"
```

---

## Task 2: The session CLI (`session_state.py`), test-first

**Files:**
- Create: `plugins/stick-shift/scripts/session_state.py`
- Test: `plugins/stick-shift/scripts/test_session_state.py`

This task builds the CLI in TDD groups. The test file mirrors `test_sdlc_state.py`:
it loads the script by path with `importlib` and re-points the module's path constants
at `tmp_path`.

- [ ] **Step 1: Write the test harness + first failing tests (init / state / status)**

Create `plugins/stick-shift/scripts/test_session_state.py`:

```python
# ABOUTME: Tests for the stick-shift session_state.py manual session CLI.
# ABOUTME: Loads the script by path and re-points its .sdlc/ paths at a tmp dir.
"""Run: `python3 -m pytest plugins/stick-shift/scripts/test_session_state.py -v`
(or plain `python3 test_session_state.py` from this dir for the fallback runner)."""

import importlib.util
import json
import os
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "session_state", Path(__file__).with_name("session_state.py")
)
session_state = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(session_state)


def _point_at(tmp_path):
    session_state.SDLC_DIR = Path(".sdlc")
    session_state.STATE_FILE = session_state.SDLC_DIR / "state.json"
    session_state.PROGRESS_FILE = session_state.SDLC_DIR / "progress.md"
    session_state.DECISIONS_FILE = session_state.SDLC_DIR / "decisions.jsonl"


def _run(tmp_path, fn, **ns):
    """Chdir into tmp_path, re-point paths, call a cmd_* fn with a Namespace."""
    cwd = Path.cwd()
    os.chdir(tmp_path)
    _point_at(tmp_path)
    try:
        fn(session_state.argparse.Namespace(**ns))
    finally:
        os.chdir(cwd)


def _init(tmp_path, feature="cart-pricing", request="Build a cart engine"):
    _run(tmp_path, session_state.cmd_init, feature=feature, request=request)
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        return json.loads(session_state.STATE_FILE.read_text())
    finally:
        os.chdir(cwd)


def test_init_creates_session_in_INIT(tmp_path):
    state = _init(tmp_path)
    assert state["state"] == "INIT"
    assert state["feature"] == "cart-pricing"
    assert state["in_flight"] == []
    assert state["history"][0]["to"] == "INIT"


def test_init_is_idempotent(tmp_path):
    _init(tmp_path)
    # Second init must not clobber — it resumes.
    state = _init(tmp_path)
    assert state["state"] == "INIT"
    assert len(state["history"]) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest plugins/stick-shift/scripts/test_session_state.py -v`
Expected: FAIL — `session_state.py` does not exist / `cmd_init` undefined.

- [ ] **Step 3: Create `session_state.py` with init/state/status**

Create `plugins/stick-shift/scripts/session_state.py`:

```python
#!/usr/bin/env python3
# ABOUTME: Manual ("stick shift") session-state CLI for the disassembled SDLC workflow.
# ABOUTME: Owns .sdlc/ — phase transitions, decisions, progress — driven by hand, no loop.
"""Stick Shift session state.

A trimmed, manually-driven sibling of autonomous-sdlc's sdlc_state.py: it shares the
.sdlc/ on-disk session format (state.json, progress.md, decisions.jsonl) but drops the
autonomous machinery (tick budgets, Stop-hook driver, attempt counters). You drive the
phase transitions yourself via slash commands.

Usage:
    session_state.py init --feature cart-pricing --request "Build a cart engine"
    session_state.py state
    session_state.py status
    session_state.py transition PLAN --reason "spec written, 3 criteria"
    session_state.py decide --decision "Decimal not float" --why "exact rounding"
    session_state.py note-progress --what "subtotal task green"
    session_state.py task t1            # mark a task in flight
    session_state.py task t1 --done     # clear it
    session_state.py journal            # render the durable session record
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SDLC_DIR = Path(".sdlc")
STATE_FILE = SDLC_DIR / "state.json"
DECISIONS_FILE = SDLC_DIR / "decisions.jsonl"
PROGRESS_FILE = SDLC_DIR / "progress.md"

STATES = ["INIT", "SPEC", "PLAN", "BUILD", "VERIFY", "DONE"]

# Normal forward/backward edges. Off-graph transitions are allowed but earn a
# one-line nudge to stderr — guidance, not bureaucracy (you are the driver).
NORMAL_EDGES = {
    "INIT": {"SPEC"},
    "SPEC": {"PLAN"},
    "PLAN": {"BUILD", "PLAN"},
    "BUILD": {"BUILD", "VERIFY"},
    "VERIFY": {"BUILD", "DONE"},
    "DONE": set(),
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load():
    if not STATE_FILE.exists():
        sys.exit("No .sdlc/state.json — run `session_state.py init` first.")
    try:
        return json.loads(STATE_FILE.read_text())
    except ValueError as e:
        sys.exit(f"CORRUPT {STATE_FILE}: {e}. Restore it from git or re-run init.")


def save(state):
    state["updated"] = now()
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def append_progress(line):
    with PROGRESS_FILE.open("a") as f:
        f.write(f"- {now()} {line}\n")


def cmd_init(args):
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        print(f"RESUME state={state['state']} feature={state['feature']}")
        return
    SDLC_DIR.mkdir(exist_ok=True)
    state = {
        "feature": args.feature,
        "request": args.request,
        "state": "INIT",
        "in_flight": [],
        "history": [{"at": now(), "to": "INIT", "reason": "initialized"}],
        "started": now(),
    }
    save(state)
    if not PROGRESS_FILE.exists():
        PROGRESS_FILE.write_text(
            f"# Progress: {args.feature}\n\nRequest: {args.request}\n\n"
        )
    append_progress("stick-shift session initialized")
    print(f"INIT feature={args.feature}")


def cmd_state(_args):
    print(load()["state"])


def cmd_status(_args):
    s = load()
    print(f"STATE={s['state']}")
    print(f"feature: {s['feature']}")
    print(f"request: {s['request']}")
    print(f"in flight: {', '.join(s.get('in_flight', [])) or '-'}")
    decisions = (
        len(DECISIONS_FILE.read_text().splitlines()) if DECISIONS_FILE.exists() else 0
    )
    print(f"decisions logged: {decisions}")
    for h in s["history"][-3:]:
        print(f"  {h['at']} → {h['to']}: {h['reason']}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="create .sdlc/ session (idempotent: resumes)")
    sp.add_argument("--feature", required=True)
    sp.add_argument("--request", default="")
    sp.set_defaults(func=cmd_init)

    sub.add_parser("state", help="print just the state name").set_defaults(
        func=cmd_state
    )
    sub.add_parser("status", help="human-readable summary").set_defaults(
        func=cmd_status
    )

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify init passes**

Run: `python3 -m pytest plugins/stick-shift/scripts/test_session_state.py -v`
Expected: PASS for `test_init_creates_session_in_INIT` and `test_init_is_idempotent`.

- [ ] **Step 5: Add failing tests for transition + friendly nudge**

Append to `test_session_state.py`:

```python
def test_transition_records_history_and_state(tmp_path):
    _init(tmp_path)
    _run(tmp_path, session_state.cmd_transition, target="SPEC", reason="3 criteria")
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        state = json.loads(session_state.STATE_FILE.read_text())
    finally:
        os.chdir(cwd)
    assert state["state"] == "SPEC"
    assert state["history"][-1] == {
        "at": state["history"][-1]["at"],
        "to": "SPEC",
        "reason": "3 criteria",
    }


def test_off_graph_transition_nudges_but_proceeds(tmp_path, capsys):
    _init(tmp_path)  # state INIT
    # INIT normally → SPEC; jumping straight to BUILD must warn yet still record.
    _run(tmp_path, session_state.cmd_transition, target="BUILD", reason="skipping ahead")
    err = capsys.readouterr().err
    assert "NUDGE" in err
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        state = json.loads(session_state.STATE_FILE.read_text())
    finally:
        os.chdir(cwd)
    assert state["state"] == "BUILD"


def test_unknown_state_is_rejected(tmp_path):
    import pytest

    _init(tmp_path)
    with pytest.raises(SystemExit):
        _run(tmp_path, session_state.cmd_transition, target="WAT", reason="x")
```

- [ ] **Step 6: Run to verify the new tests fail**

Run: `python3 -m pytest plugins/stick-shift/scripts/test_session_state.py -v`
Expected: FAIL — `cmd_transition` undefined.

- [ ] **Step 7: Add `cmd_transition` and wire it**

Add this function to `session_state.py` (after `cmd_status`):

```python
def cmd_transition(args):
    target = args.target.upper()
    if target not in STATES:
        sys.exit(f"Unknown state {target}. States: {', '.join(STATES)}")
    s = load()
    if target not in NORMAL_EDGES.get(s["state"], set()):
        normal = ", ".join(sorted(NORMAL_EDGES.get(s["state"], set()))) or "(none)"
        print(
            f"NUDGE {s['state']} usually goes to: {normal}. "
            f"Recording {s['state']} → {target} anyway — you're driving.",
            file=sys.stderr,
        )
    s["history"].append({"at": now(), "to": target, "reason": args.reason})
    s["state"] = target
    save(s)
    append_progress(f"→ {target}: {args.reason}")
    print(f"OK {target}")
```

Add this parser block inside `main()` (before `args = p.parse_args()`):

```python
    sp = sub.add_parser("transition", help="move to a phase (nudge on off-graph)")
    sp.add_argument("target")
    sp.add_argument("--reason", required=True)
    sp.set_defaults(func=cmd_transition)
```

- [ ] **Step 8: Run to verify transition tests pass**

Run: `python3 -m pytest plugins/stick-shift/scripts/test_session_state.py -v`
Expected: PASS (all five tests so far).

- [ ] **Step 9: Add failing tests for decide / note-progress / task / journal**

Append to `test_session_state.py`:

```python
def test_decide_appends_jsonl(tmp_path):
    _init(tmp_path)
    _run(
        tmp_path,
        session_state.cmd_decide,
        decision="Decimal not float",
        why="exact rounding",
        irreversible=False,
    )
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        lines = session_state.DECISIONS_FILE.read_text().splitlines()
    finally:
        os.chdir(cwd)
    entry = json.loads(lines[0])
    assert entry["decision"] == "Decimal not float"
    assert entry["why"] == "exact rounding"
    assert entry["reversible"] is True


def test_task_in_flight_add_and_done(tmp_path):
    _init(tmp_path)
    _run(tmp_path, session_state.cmd_task, task_id="t1", done=False)
    _run(tmp_path, session_state.cmd_task, task_id="t2", done=False)
    _run(tmp_path, session_state.cmd_task, task_id="t1", done=True)
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        state = json.loads(session_state.STATE_FILE.read_text())
    finally:
        os.chdir(cwd)
    assert state["in_flight"] == ["t2"]


def test_journal_renders_history_and_decisions(tmp_path, capsys):
    _init(tmp_path)
    _run(tmp_path, session_state.cmd_transition, target="SPEC", reason="3 criteria")
    _run(
        tmp_path,
        session_state.cmd_decide,
        decision="Decimal not float",
        why="exact rounding",
        irreversible=False,
    )
    _run(tmp_path, session_state.cmd_journal)
    out = capsys.readouterr().out
    assert "cart-pricing" in out
    assert "→ SPEC: 3 criteria" in out
    assert "Decimal not float" in out
```

- [ ] **Step 10: Run to verify they fail**

Run: `python3 -m pytest plugins/stick-shift/scripts/test_session_state.py -v`
Expected: FAIL — `cmd_decide`, `cmd_task`, `cmd_journal`, `cmd_note_progress` undefined.

- [ ] **Step 11: Add the remaining commands**

Add these functions to `session_state.py` (after `cmd_transition`):

```python
def cmd_decide(args):
    s = load()
    SDLC_DIR.mkdir(exist_ok=True)
    entry = {
        "at": now(),
        "state": s["state"],
        "decision": args.decision,
        "why": args.why,
        "reversible": not args.irreversible,
    }
    with DECISIONS_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print("OK decision logged")


def cmd_note_progress(args):
    load()  # ensure a session exists
    append_progress(args.what)
    print("OK")


def cmd_task(args):
    s = load()
    in_flight = s.get("in_flight", [])
    if args.done:
        if args.task_id in in_flight:
            in_flight.remove(args.task_id)
    elif args.task_id not in in_flight:
        in_flight.append(args.task_id)
    s["in_flight"] = in_flight
    save(s)
    print(f"OK in_flight=[{', '.join(in_flight) or '-'}]")


def cmd_journal(_args):
    s = load()
    print(f"# Session journal: {s['feature']}")
    print(f"Request: {s['request']}")
    print(f"State: {s['state']}\n")
    print("## Phase history")
    for h in s["history"]:
        print(f"- {h['at']} → {h['to']}: {h['reason']}")
    print("\n## Decisions")
    if DECISIONS_FILE.exists():
        for line in DECISIONS_FILE.read_text().splitlines():
            d = json.loads(line)
            tag = "" if d.get("reversible", True) else " (irreversible)"
            print(f"- [{d['state']}] {d['decision']} — {d['why']}{tag}")
    else:
        print("- (none logged)")
```

Add these parser blocks inside `main()` (before `args = p.parse_args()`):

```python
    sp = sub.add_parser("decide", help="log a decision to decisions.jsonl")
    sp.add_argument("--decision", required=True)
    sp.add_argument("--why", required=True)
    sp.add_argument("--irreversible", action="store_true")
    sp.set_defaults(func=cmd_decide)

    sp = sub.add_parser("note-progress", help="append a progress line")
    sp.add_argument("--what", required=True)
    sp.set_defaults(func=cmd_note_progress)

    sp = sub.add_parser("task", help="mark a task in flight (or --done)")
    sp.add_argument("task_id")
    sp.add_argument("--done", action="store_true")
    sp.set_defaults(func=cmd_task)

    sub.add_parser("journal", help="render the durable session record").set_defaults(
        func=cmd_journal
    )
```

- [ ] **Step 12: Run the full suite to verify all pass**

Run: `python3 -m pytest plugins/stick-shift/scripts/test_session_state.py -v`
Expected: PASS — all eight tests green.

- [ ] **Step 13: Commit**

```bash
git add plugins/stick-shift/scripts/session_state.py plugins/stick-shift/scripts/test_session_state.py
git commit -m "feat(stick-shift): manual session_state.py CLI with tests"
```

---

## Task 3: The five command files

**Files:**
- Create: `plugins/stick-shift/commands/spec.md`
- Create: `plugins/stick-shift/commands/plan.md`
- Create: `plugins/stick-shift/commands/build.md`
- Create: `plugins/stick-shift/commands/verify.md`
- Create: `plugins/stick-shift/commands/journal.md`

- [ ] **Step 1: Create `commands/spec.md`**

```markdown
---
name: spec
description: Stick Shift phase 1 — turn a task into 3–5 Given/When/Then acceptance criteria, init the session, and stop. You choose when to /plan.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
argument-hint: "<what to build>"
---

# /spec — define "done" before any code

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py` (run with `python3`).

The user wants to build: $ARGUMENTS

Do exactly one phase, then stop and hand control back.

1. **Init the session (idempotent).** Derive a short `{slug}` ("Build a cart pricing
   engine" → `cart-pricing`).
   - `python3 $STATE init --feature {slug} --request "$ARGUMENTS"`
   - If it prints `RESUME`, the session exists — read `.sdlc/` and continue rather than
     re-initializing.
   - Create a branch if not on one: `git checkout -b stickshift/{slug}`.
2. **Write 3–5 acceptance criteria** in Given/When/Then form to `specs/{slug}-spec.md`,
   numbered AC-1, AC-2, … Keep it tight — a cold live build, not an exhaustive spec.
   Each criterion must be concrete and testable.
3. **Log any assumption you make** with `python3 $STATE decide --decision "..." --why
   "..."` (e.g. "discounts apply before tax"). Decide, don't ask.
4. **Record + commit:** `python3 $STATE transition SPEC --reason "wrote N criteria"`,
   then `git add -A && git commit -m "spec({slug}): N acceptance criteria"`.
5. **Stop. Hand control back.** End with the criteria, any decision logged, and one
   line: "Spec ready. Run `/plan` when you want me to decompose it — your call."

Do NOT start planning or coding. One phase per command.
```

- [ ] **Step 2: Create `commands/plan.md`**

```markdown
---
name: plan
description: Stick Shift phase 2 — decompose the spec into a short task list, log key decisions, and stop. You choose when to /build.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
---

# /plan — decompose and decide

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py`

Do exactly one phase, then stop.

1. **Orient:** `python3 $STATE status`; read `specs/{slug}-spec.md`.
2. **Decompose** into 3–4 right-sized tasks (each TDD-able in a few minutes). Write them
   to `specs/{slug}-plan.md` as a numbered list with a one-line purpose each, noting
   which acceptance criteria each task covers.
3. **Log the load-bearing design decisions** with `python3 $STATE decide` (e.g. "Decimal
   not float for money / exact rounding"). These are your judgment beats — make them
   explicit.
4. **Record + commit:** `python3 $STATE transition PLAN --reason "N tasks"`, then
   `git add -A && git commit -m "plan({slug}): N tasks"`.
5. **Stop. Hand control back.** End with the task list and a recommendation: "N tasks
   ready; I'd start with <task> because <reason> — your call. Run `/build`."

Do NOT start coding. One phase per command.
```

- [ ] **Step 3: Create `commands/build.md`**

```markdown
---
name: build
description: Stick Shift phase 3 — implement ONE task with TDD (red→green→refactor), then stop. Run once per task.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
argument-hint: "[task number or name, optional]"
---

# /build — one task, test-first

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py`

Implement exactly ONE task with TDD, then stop.

1. **Pick the task:** if $ARGUMENTS names one, use it; else take the next task from
   `specs/{slug}-plan.md`. Mark it in flight: `python3 $STATE task <id>`.
2. **RED:** write a failing test that pins the behavior. Run it; confirm it fails for
   the right reason.
3. **GREEN:** write the minimal code to pass. Run the test; confirm green.
4. **REFACTOR:** clean up while green. Run the full suite.
5. **Record + commit:** `python3 $STATE task <id> --done`, `python3 $STATE note-progress
   --what "<id> green"`, `python3 $STATE transition BUILD --reason "closed <id>, M left"`,
   then `git add -A && git commit -m "feat({slug}): <task>"`.
6. **Stop. Hand control back.** End with what you built, the test that proves it, and
   "Task done. `/build` the next one, or `/verify` when the tasks are complete — your
   call."

If you hit ambiguity, decide and log it (`python3 $STATE decide`). One task per command.
```

- [ ] **Step 4: Create `commands/verify.md`**

```markdown
---
name: verify
description: Stick Shift phase 4 — run the suite and walk each acceptance criterion ("passing ≠ satisfied"), then stop.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
---

# /verify — prove the spec, not just green tests

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py`

1. **Mechanical:** run the full test suite (e.g. `uv run pytest -q`) and the linters the
   project uses. Report the real result — never paper over a failure.
2. **Spec compliance:** open `specs/{slug}-spec.md` and walk AC-1, AC-2, … one by one.
   For each, point to the test or behavior that demonstrably satisfies it. Tests passing
   is not the same as the spec being met.
3. **Record + commit fixes:**
   - All green and every criterion met → `python3 $STATE transition DONE --reason "all N
     criteria met"`.
   - Anything red or unmet → `python3 $STATE transition BUILD --reason "AC-k unmet"` and
     name the gap so the next `/build` fixes it.
4. **Stop. Hand control back.** End with a per-criterion checklist (met/unmet) and the
   next move. Optionally suggest the built-in `/code-review` skill before the close.

One phase per command.
```

- [ ] **Step 5: Create `commands/journal.md`**

```markdown
---
name: journal
description: Stick Shift close — render the durable session record (phase history + every logged decision + criterion status). The "session that survives" beat.
allowed-tools:
  - Read
  - Bash
---

# /journal — the durable session record

`STATE=${CLAUDE_PLUGIN_ROOT}/scripts/session_state.py`

1. Run `python3 $STATE journal` and show the output: the phase history and every
   decision logged this session, straight from `.sdlc/`.
2. Read `specs/{slug}-spec.md` and append a final acceptance-criteria checklist
   (met / unmet), citing the test or behavior for each.
3. Narrate the close: this `.sdlc/` record is the durable session — it survived the
   whole build and is exactly what a shared corpus (e.g. compound-knowledge) would
   ingest. The harness was disposable; the session is the thing that survived.

Read-only — this command reports, it does not change state.
```

- [ ] **Step 6: Sanity-check the command frontmatter parses**

Run:
```bash
python3 - <<'PY'
import pathlib, re
for f in sorted(pathlib.Path("plugins/stick-shift/commands").glob("*.md")):
    text = f.read_text()
    assert text.startswith("---\n"), f"{f}: missing frontmatter"
    fm = text.split("---\n", 2)[1]
    assert "name:" in fm and "description:" in fm, f"{f}: missing name/description"
    print(f"OK {f.name}")
PY
```
Expected: `OK spec.md` … `OK journal.md` for all five.

- [ ] **Step 7: Commit**

```bash
git add plugins/stick-shift/commands/
git commit -m "feat(stick-shift): five manual phase commands"
```

---

## Task 4: Register in the marketplace

**Files:**
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Add the plugin entry**

In `.claude-plugin/marketplace.json`, append this object to the `plugins` array (after
the `review-diff` entry):

```json
    {
      "name": "stick-shift",
      "source": "./plugins/stick-shift",
      "description": "Manually-driven (\"disassembled\") SDLC: the same .sdlc/ session format as autonomous-sdlc, but you drive each phase by hand via slash commands — /spec → /plan → /build (TDD) → /verify → /journal. Built for legible, narratable live demos.",
      "version": "0.1.0",
      "author": {
        "name": "Joshua Oliphant"
      },
      "keywords": [
        "sdlc",
        "tdd",
        "manual",
        "session",
        "harness",
        "developer-experience",
        "demo"
      ],
      "category": "development",
      "license": "MIT"
    }
```

- [ ] **Step 2: Bump the marketplace catalog version**

A plugin was added, so bump `metadata.version` in `.claude-plugin/marketplace.json` from
`1.0.8` to `1.0.9`.

- [ ] **Step 3: Run the version sync check**

Run: `python3 scripts/check_marketplace_versions.py`
Expected: `OK: 9 plugin versions in sync.` (8 existing + stick-shift).

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat(stick-shift): register plugin in marketplace (catalog 1.0.9)"
```

---

## Task 5: End-to-end rehearsal dry run

This task proves the whole workflow on a throwaway repo — the interview rehearsal. No new
plugin code; it validates the plugin behaves as designed. Run it with the plugin
installed locally (`claude --plugin-dir /path/to/claude-plugins`).

- [ ] **Step 1: Create a scratch repo**

```bash
mkdir -p /tmp/stickshift-rehearsal && git -C /tmp/stickshift-rehearsal init -q
```
Open a Claude Code session there with the plugin available.

- [ ] **Step 2: Run the full arc and confirm each beat**

Drive the five commands against a representative task and confirm the on-disk session:
```
/spec "Build a cart pricing engine: subtotal, stackable discounts, tax, rounding"
/plan
/build
/build
/verify
/journal
```
After the run, confirm in the scratch repo:
```bash
python3 /path/to/claude-plugins/plugins/stick-shift/scripts/session_state.py status
test -f .sdlc/state.json && test -f .sdlc/decisions.jsonl && echo "session present ✓"
```
Expected: `STATE=DONE` (or `VERIFY`/`BUILD` if you stopped early), a non-empty
`decisions.jsonl`, and `/journal` rendering the phase history + decisions.

- [ ] **Step 3: Time it**

Run the arc end-to-end against a clock. Confirm it fits inside ~55 minutes of driving
with buffer. If any single command's instructions feel like ceremony during the run,
note it — the design's stated failure mode is "process for its own sake." Trim in a
follow-up.

- [ ] **Step 4: Clean up**

```bash
rm -rf /tmp/stickshift-rehearsal
```

No commit (validation only).

---

## Self-Review

**Spec coverage:**
- Shared Session / swappable manual Harness → `session_state.py` (`.sdlc/` format) + command-driven transitions (Tasks 2, 3). ✓
- Five commands `/spec /plan /build /verify /journal` → Task 3. ✓
- Pruned INIT (folded into `/spec`), REVIEW (built-in `/code-review`, referenced in `/verify`), SHIP (dropped; `/journal` closes) → Tasks 2–3. ✓
- Trimmed `session_state.py` (no tick/driver/budgets) → Task 2 (only init/state/status/transition/decide/note-progress/task/journal). ✓
- Friendly nudge, not hard block → `cmd_transition` nudge path + `test_off_graph_transition_nudges_but_proceeds` (Task 2). ✓
- Self-contained (no dependency on autonomous-sdlc) → stdlib-only CLI, inline command guidance (Tasks 2–3). ✓
- New plugin + marketplace registration → Tasks 1, 4. ✓
- Multiplayer-gap answer (corpus) → narrated in `/journal` (Task 3, Step 5). ✓
- Rehearse before interview day → Task 5. ✓

**Placeholder scan:** No TBD/TODO; every code and command step shows complete content. ✓

**Type/name consistency:** `cmd_init/state/status/transition/decide/note_progress/task/journal`, `NORMAL_EDGES`, `STATES`, and the `.sdlc/` path constants are used identically across the implementation and tests. Subcommand names (`init`, `state`, `status`, `transition`, `decide`, `note-progress`, `task`, `journal`) match between `main()` wiring and the command files. ✓

**Deferred (post-interview, per design open questions):** `sync_shared.py` wiring for `session_state.py`; extracting phase guidance into tiny skills if rehearsal shows a reason. Both intentionally out of scope.
