#!/usr/bin/env python3
# ABOUTME: State machine CLI for the autonomous-sdlc loop.
# ABOUTME: Owns .sdlc/state.json — transitions, budgets, decisions, progress.
"""SDLC loop state machine.

Every loop iteration starts by calling `tick` and ends by calling
`transition` or `note-progress`. The loop driver (the plugin's Stop hook,
or a user-armed self-paced `/loop`) reads `state` to decide whether the loop
may exit. All state lives in
.sdlc/ in the current working directory so any fresh context can resume.

Usage:
    sdlc_state.py init --feature user-auth --request "Add auth" [--max-iterations 50]
                       [--reviewers code-review,security-review] [--review-mode block]
                       [--intent specs/user-auth-intent.md] [--gate plan,ship]
    sdlc_state.py gate plan                # pause for human review if --gate plan was set (else OPEN)
    sdlc_state.py fix-task bd-c3d4         # register a VERIFY/REVIEW fix task: test files lock while it is in flight
    sdlc_state.py fix-task bd-c3d4 --unlock --reason "the test itself was wrong"
    sdlc_state.py state                    # prints just the state name (for evaluators)
    sdlc_state.py status                   # human-readable summary
    sdlc_state.py tick                     # start a WORK iteration: bump counter, enforce budgets
    sdlc_state.py tick --waiting           # a wait-check on in-flight agents: free, not budgeted
    sdlc_state.py transition BUILD --reason "plan committed, 6 tasks ready"
    sdlc_state.py increment --feature phase-2 --request "..."  # after DONE: start the next increment
    sdlc_state.py task bd-a1b2             # mark a task in flight (multiple allowed)
    sdlc_state.py task bd-a1b2 --done      # remove it from the in-flight set
    sdlc_state.py attempt bd-a1b2          # count an attempt; exit 1 when budget exceeded
    sdlc_state.py set-budget --max-iterations 120   # adjust budgets mid-loop (log a decision too)
    sdlc_state.py set-driver loop          # record that the user armed a bare /loop (stands the hook down)
    sdlc_state.py decide --decision "JWT RS256 over HS256" --why "..." [--irreversible]
    sdlc_state.py note-progress --what "closed bd-a1b2"
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
# Project-level prompt that a bare `/loop` runs (self-paced: Claude picks the
# delay between iterations and ends the loop itself). Regenerated on every
# `init` (fresh, resume, or increment) so the feature line and the baked CLI
# path never go stale, and removed when the loop reaches DONE or BLOCKED so a
# later bare `/loop` runs the built-in PR-maintenance prompt, not the ritual.
# The file is only touched when it carries our marker line: a user's own
# loop.md is never overwritten or deleted.
LOOP_MD_FILE = Path(".claude") / "loop.md"
LOOP_MD_MARKER = "# autonomous-sdlc loop prompt"

# auto: the plugin's Stop hook drives. loop: the user armed a bare /loop and
# said so (set-driver loop), which stands the hook down. goal is kept for loops
# recorded before /loop existed; stop-hook forces the hook explicitly.
DRIVERS = ("auto", "loop", "goal", "stop-hook")

# Opt-in human approval gates (playbook: "approved plan committed before code",
# "hooks as approval gates"). A gate reuses BLOCKED: `gate <name>` pauses the
# loop with an escalation file, and the next `init` (a re-run of /sdlc) records
# the gate as passed and resumes at GATE_RESUME[name]. No new states.
GATES = ("plan", "ship")
GATE_RESUME = {"plan": "BUILD", "ship": "SHIP"}
GATE_REASON_PREFIX = "gate: "
ESCALATION_FILE = SDLC_DIR / "escalation.md"

STATES = [
    "INIT",
    "SPEC",
    "PLAN",
    "BUILD",
    "VERIFY",
    "REVIEW",
    "SHIP",
    "REPAIR",
    "DONE",
    "BLOCKED",
]

ACTIVE_STATES = [s for s in STATES if s not in ("DONE", "BLOCKED")]

# Forward edges plus the loop's defining backward edges. REPAIR is reachable
# from every active state (broken branch is always possible), BLOCKED from
# everywhere (escalation is always a legal exit).
TRANSITIONS = {
    "INIT": {"SPEC"},
    "SPEC": {"PLAN"},
    "PLAN": {"BUILD", "PLAN"},  # one re-plan allowed
    "BUILD": {"BUILD", "VERIFY"},  # one task per iteration
    "VERIFY": {"BUILD", "REVIEW"},  # red → back to BUILD with a fix task
    "REVIEW": {"BUILD", "SHIP"},  # findings → back to BUILD
    "SHIP": {"DONE"},
    "REPAIR": {"BUILD", "VERIFY"},  # fixed forward, resume where sensible
    "DONE": set(),
    "BLOCKED": set(ACTIVE_STATES),  # human restart resumes the loop
}
for _s in ACTIVE_STATES:
    TRANSITIONS[_s] = TRANSITIONS[_s] | {"REPAIR", "BLOCKED"}

NO_PROGRESS_LIMIT = 2  # idle iterations before forced BLOCKED

# Per-project REVIEW-gate config. The default preserves v2.0.0 behavior: the
# built-in code-review skill, blocking (findings become fix tasks → BUILD).
DEFAULT_REVIEWERS = ["code-review"]
REVIEW_MODES = ("block", "annotate")
DEFAULT_REVIEW_MODE = "block"


def build_review_config(reviewers: str | None, mode: str | None) -> dict:
    """Parse the --reviewers/--review-mode init flags into a review config block.

    reviewers: comma-separated reviewer names (skills or pr-review-toolkit
    agents). Blank/None falls back to DEFAULT_REVIEWERS so the gate is never
    empty. mode: "block" or "annotate"; None falls back to DEFAULT_REVIEW_MODE.
    """
    names = [r.strip() for r in (reviewers or "").split(",") if r.strip()]
    if not names:
        names = list(DEFAULT_REVIEWERS)
    chosen_mode = mode or DEFAULT_REVIEW_MODE
    # This function is the authoritative mode validator: it has non-CLI callers
    # (the test suite, and the resume backfill above) that bypass argparse. The
    # init parser's choices=list(REVIEW_MODES) is kept purely for CLI UX (a
    # clean argparse error before we get here).
    if chosen_mode not in REVIEW_MODES:
        sys.exit(
            f"Invalid --review-mode {chosen_mode!r}; choose one of {REVIEW_MODES}."
        )
    return {"reviewers": names, "mode": chosen_mode}


def parse_gates(gates: str | None) -> list[str]:
    """Parse the --gate init flag (comma-separated gate names) and validate it."""
    names = [g.strip() for g in (gates or "").split(",") if g.strip()]
    unknown = [g for g in names if g not in GATES]
    if unknown:
        sys.exit(f"Unknown --gate {unknown}; choose from {', '.join(GATES)}.")
    return list(dict.fromkeys(names))  # dedupe, keep order


def default_intent(feature: str) -> str:
    return f"specs/{feature}-intent.md"


def resolve_intent(intent: str | None, feature: str) -> str:
    """The intent document path recorded in state.json.

    Given explicitly (`/sdlc specs/foo-intent.md`), the file must already exist:
    it is the human's input. Omitted, the default path is recorded and the INIT
    dispatch writes the document from the request sentence, so every loop has a
    committed intent artifact the spec and the PR trace back to.
    """
    if intent:
        if not Path(intent).exists():
            sys.exit(f"--intent {intent} does not exist.")
        return intent
    return default_intent(feature)


def gate_escalation_text(name: str, state: dict) -> str:
    feature, request = state["feature"], state.get("request", "")
    rerun = f'/sdlc "{request}"' if request else "/sdlc"
    if name == "plan":
        return (
            "# Gate: plan review\n\n"
            "The loop paused on purpose (`--gate plan`), after the plan was committed and "
            "before any code was written.\n\n"
            f"1. Review `specs/{feature}-plan.md` (and `specs/{feature}-spec.md`).\n"
            "2. Edit either file in place if you want changes; the loop reads them from disk.\n"
            f"3. Re-run `{rerun}`. The resume records the gate as passed and continues into BUILD.\n"
        )
    return (
        "# Gate: ship review\n\n"
        "The loop paused on purpose (`--gate ship`), before opening the pull request. "
        "The feature branch is already pushed to the remote (no PR yet).\n\n"
        "1. Review the branch: `git log --oneline main..HEAD`, `git diff main...HEAD`, and "
        "`.sdlc/decisions.jsonl`.\n"
        "2. Fix anything by hand, commit it on the feature branch, and push again.\n"
        f"3. Re-run `{rerun}`. The resume continues in SHIP and opens the PR.\n"
    )


LOOP_MD_TEMPLATE = """\
{marker} (written by `sdlc_state.py init`; a bare `/loop` runs it)

<!-- Machine-local: the state CLI path below is absolute for THIS checkout and
     plugin install. Do not commit this file (add `.claude/loop.md` to .gitignore);
     every `/sdlc` rewrites it and DONE/BLOCKED removes it. -->

You are one iteration of the autonomous-sdlc loop for **{feature}**. Follow the
`sdlc-loop` skill's iteration ritual exactly, then stop:

0. If this session has not invoked the `sdlc-loop` skill yet, invoke it now with the
   Skill tool (not Read): its frontmatter registers the loop's permission rails and
   test-lock hooks for the session.
1. `python3 {state_cli} tick` (or `tick --waiting` if this iteration only checks on
   in-flight builders). If it prints `DONE` or `BLOCKED`, the loop is finished: end
   this /loop (`ScheduleWakeup` with `stop: true`), report the final status, and stop.
2. Orient: `python3 {state_cli} status`, tail `.sdlc/progress.md`, `git log --oneline -10`,
   and `.sdlc/signs.md` if it exists.
3. Do ONE unit of work for the current state (dispatch table in the `sdlc-loop` skill).
4. Commit, then `note-progress` or `transition`.
5. Pace the next wakeup: builders still in flight, wait 5 to 15 minutes; ready work,
   1 minute; every remaining task blocked, escalate (`transition BLOCKED`) and end the loop.
"""


def loop_md_is_ours() -> bool:
    """True when .claude/loop.md exists and was generated by this CLI."""
    try:
        return LOOP_MD_FILE.read_text().startswith(LOOP_MD_MARKER)
    except OSError:
        return False


def write_loop_md(feature: str) -> bool:
    """(Re)write .claude/loop.md for the native /loop driver. Returns True if written.

    Regenerates our own file on every call so the feature line tracks the current
    increment and the baked state-CLI path tracks the current plugin install
    (`.claude/loop.md` is project content, so `${CLAUDE_PLUGIN_ROOT}` would not be
    expanded there). A loop.md without our marker belongs to the user and is
    left untouched.
    """
    if LOOP_MD_FILE.exists() and not loop_md_is_ours():
        return False
    LOOP_MD_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOOP_MD_FILE.write_text(
        LOOP_MD_TEMPLATE.format(
            marker=LOOP_MD_MARKER,
            feature=feature,
            state_cli=Path(__file__).resolve(),
        )
    )
    return True


def remove_loop_md() -> bool:
    """Delete .claude/loop.md when it is ours. Returns True if removed.

    Called when the loop reaches a terminal state (DONE, BLOCKED) so a bare
    `/loop` afterwards runs Claude Code's built-in PR-maintenance prompt instead
    of re-entering a finished ritual. A user's own loop.md is never deleted.
    """
    if not loop_md_is_ours():
        return False
    LOOP_MD_FILE.unlink()
    return True


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load() -> dict:
    if not STATE_FILE.exists():
        sys.exit("No .sdlc/state.json — run `sdlc_state.py init` first.")
    try:
        return json.loads(STATE_FILE.read_text())
    except ValueError as e:
        sys.exit(
            f"CORRUPT {STATE_FILE}: {e}. Restore it from git "
            f"(git checkout -- {STATE_FILE}) or re-run init after removing it."
        )


def save(state: dict) -> None:
    state["updated"] = now()
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def append_progress(line: str) -> None:
    with PROGRESS_FILE.open("a") as f:
        f.write(f"- {now()} {line}\n")


def cmd_init(args: argparse.Namespace) -> None:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        # Backfill the review gate for loops initialized before it existed
        # (pre-2.1.0 state.json has no "review" key, which would KeyError the
        # REVIEW-state reader). Only write when we actually added it, so resume
        # of an already-current file is a no-op.
        if "review" not in state:
            state["review"] = build_review_config(None, None)
            save(state)
        # Same backfill for the 2.5.0 fields (intent, gates, fix tasks).
        added = False
        for key, value in (
            ("intent", default_intent(state["feature"])),
            ("gates", []),
            ("gates_passed", []),
            ("fix_tasks", []),
        ):
            if key not in state:
                state[key] = value
                added = True
        if added:
            save(state)
        # A loop paused at an approval gate resumes by the human re-running /sdlc:
        # record the gate as passed and continue at the state the gate guards.
        last_reason = (state["history"][-1] if state["history"] else {}).get("reason", "")
        if state["state"] == "BLOCKED" and last_reason.startswith(GATE_REASON_PREFIX):
            name = last_reason[len(GATE_REASON_PREFIX) :].strip()
            target = GATE_RESUME.get(name)
            if target:
                state["gates_passed"].append(name)
                state["history"].append(
                    {"at": now(), "to": target, "reason": f"gate {name} passed by human"}
                )
                state["state"] = target
                state["last_progress_iteration"] = state["iteration"]
                save(state)
                append_progress(f"→ {target}: gate {name} passed (human re-ran /sdlc)")
                write_loop_md(state["feature"])
                print(
                    f"RESUME state={target} iteration={state['iteration']} gate={name} passed"
                )
                return
        # A finished (DONE) loop re-invoked with a *new* feature is the next
        # increment, not a resume: archive the finished increment and reset to
        # INIT so a plain `/sdlc "new thing"` works in the same project instead
        # of silently resuming DONE and dropping the new request. Same feature
        # on DONE is a true no-op resume; a non-DONE state always resumes live
        # work untouched (never increment over a loop still in flight).
        if state["state"] == "DONE" and args.feature != state["feature"]:
            apply_increment(
                state, args.feature, args.request, getattr(args, "intent", None)
            )
            save(state)
            append_progress(
                f"━━ increment {state['cycle']}: {args.feature} — {args.request}"
            )
            write_loop_md(args.feature)
            print(f"INCREMENT cycle={state['cycle']} feature={args.feature} state=INIT")
            return
        # Resume regenerates loop.md too (a BLOCKED loop removed it; a stale one
        # may bake a path from a plugin version that no longer exists).
        if state["state"] in ACTIVE_STATES or state["state"] == "BLOCKED":
            write_loop_md(state["feature"])
        print(f"RESUME state={state['state']} iteration={state['iteration']}")
        return
    intent = resolve_intent(getattr(args, "intent", None), args.feature)
    gates = parse_gates(getattr(args, "gates", None))
    SDLC_DIR.mkdir(exist_ok=True)
    state = {
        "feature": args.feature,
        "request": args.request,
        "intent": intent,
        "gates": gates,
        "gates_passed": [],
        "fix_tasks": [],
        "state": "INIT",
        "cycle": 1,
        "driver": args.driver,
        "iteration": 0,
        "budgets": {
            "max_iterations": args.max_iterations,
            "max_attempts_per_task": args.max_attempts,
            "max_wait_ticks": args.max_wait_ticks,
        },
        "in_flight": [],
        "increments": [],
        "wait_ticks": 0,
        "attempts": {},
        "review": build_review_config(
            getattr(args, "reviewers", None), getattr(args, "review_mode", None)
        ),
        "last_progress_iteration": 0,
        "history": [{"at": now(), "to": "INIT", "reason": "initialized", "cycle": 1}],
        "started": now(),
    }
    save(state)
    if not PROGRESS_FILE.exists():
        PROGRESS_FILE.write_text(
            f"# Progress: {args.feature}\n\nRequest: {args.request}\n\n"
        )
    if write_loop_md(args.feature):
        append_progress(f"wrote {LOOP_MD_FILE} (bare /loop drives the ritual)")
    else:
        append_progress(f"kept user-owned {LOOP_MD_FILE} (no marker line)")
    append_progress(f"loop initialized (driver={args.driver})")
    gate_note = f" gates={','.join(gates)}" if gates else ""
    print(f"INIT feature={args.feature} driver={args.driver} intent={intent}{gate_note}")


def cmd_state(_args: argparse.Namespace) -> None:
    print(load()["state"])


def cmd_status(_args: argparse.Namespace) -> None:
    s = load()
    b = s["budgets"]
    print(f"STATE={s['state']} (cycle {s.get('cycle', 1)})")
    print(f"feature: {s['feature']}")
    prior = s.get("increments", [])
    if prior:
        names = ", ".join(f"{i['cycle']}:{i['feature']}" for i in prior)
        print(f"prior increments: {names}")
    print(f"iteration: {s['iteration']}/{b['max_iterations']}")
    print(f"wait ticks: {s.get('wait_ticks', 0)}/{b.get('max_wait_ticks', '-')}")
    in_flight = s.get("in_flight") or (
        [s["current_task"]] if s.get("current_task") else []
    )
    print(f"in flight: {', '.join(in_flight) or '-'}")
    fix_tasks = s.get("fix_tasks", [])
    locked = sorted(set(fix_tasks) & set(in_flight))
    print(
        f"fix tasks: {', '.join(fix_tasks) or '-'}"
        + (f" (test files LOCKED for {', '.join(locked)})" if locked else "")
    )
    print(f"intent: {s.get('intent', '-')}")
    gates = s.get("gates", [])
    passed = set(s.get("gates_passed", []))
    print(
        "gates: "
        + (", ".join(g + (" (passed)" if g in passed else "") for g in gates) or "-")
    )
    review = s.get("review", build_review_config(None, None))
    print(f"review gate: {', '.join(review['reviewers'])} (mode={review['mode']})")
    print(f"last progress: iteration {s['last_progress_iteration']}")
    decisions = (
        len(DECISIONS_FILE.read_text().splitlines()) if DECISIONS_FILE.exists() else 0
    )
    print(f"decisions logged: {decisions}")
    for h in s["history"][-3:]:
        print(f"  {h['at']} → {h['to']}: {h['reason']}")


def block(state: dict, reason: str) -> None:
    state["history"].append({"at": now(), "to": "BLOCKED", "reason": reason})
    state["state"] = "BLOCKED"
    save(state)
    append_progress(f"BLOCKED: {reason}")
    if remove_loop_md():
        append_progress(f"removed {LOOP_MD_FILE} (loop paused; /sdlc rewrites it)")
    print(f"BLOCKED {reason}")


def apply_increment(
    state: dict, feature: str, request: str, intent: str | None = None
) -> None:
    """Archive the current increment and reset the session onto the next one.

    DONE is a terminal sink in the edge graph and init is resume-only, so
    without this the only path to increment 2 is an off-graph DONE→SPEC nudge
    that leaves feature/request stale. This archives the finished increment,
    retargets the session, bumps the cycle so on-disk records stay grouped, and
    resets to INIT so the normal INIT→SPEC edge applies with no nudge.

    Per-run loop counters (iteration, wait_ticks, attempts, idle marker) reset —
    a new increment earns a fresh budget. Per-project config (budgets, the review
    gate, the driver) is preserved untouched.
    """
    prev_cycle = state.get("cycle", 1)
    state.setdefault("increments", []).append(
        {
            "cycle": prev_cycle,
            "feature": state["feature"],
            "request": state["request"],
            "ended_state": state["state"],
            "at": now(),
        }
    )
    new_cycle = prev_cycle + 1
    state["cycle"] = new_cycle
    state["feature"] = feature
    state["request"] = request
    state["intent"] = resolve_intent(intent, feature)
    state["gates_passed"] = []  # gates (the config) persist; passes are per increment
    state["fix_tasks"] = []
    state["state"] = "INIT"
    state["in_flight"] = []
    state["iteration"] = 0
    state["wait_ticks"] = 0
    state["attempts"] = {}
    state["last_progress_iteration"] = 0
    state["history"].append(
        {
            "at": now(),
            "to": "INIT",
            "reason": f"increment {new_cycle}: {feature}",
            "cycle": new_cycle,
        }
    )


def cmd_increment(args: argparse.Namespace) -> None:
    s = load()
    apply_increment(s, args.feature, args.request, getattr(args, "intent", None))
    save(s)
    append_progress(f"━━ increment {s['cycle']}: {args.feature} — {args.request}")
    write_loop_md(args.feature)
    print(f"OK increment {s['cycle']}: state INIT, feature={args.feature}")


def cmd_tick(args: argparse.Namespace) -> None:
    s = load()
    if s["state"] in ("DONE", "BLOCKED"):
        print(s["state"])
        return
    if args.waiting:
        # A wait-check on in-flight background agents is not a unit of work:
        # it consumes neither the iteration budget nor the idle allowance.
        # It has its own (generous) ceiling so a loop that only ever waits
        # still terminates.
        s["wait_ticks"] = s.get("wait_ticks", 0) + 1
        limit = s["budgets"].get("max_wait_ticks", 200)
        if s["wait_ticks"] > limit:
            block(s, f"budget: max_wait_ticks={limit} exhausted while waiting")
            sys.exit(1)
        save(s)
        in_flight = ", ".join(s.get("in_flight", [])) or "-"
        print(
            f"WAITING {s['wait_ticks']}/{limit} STATE={s['state']} in_flight={in_flight}"
        )
        return
    s["iteration"] += 1
    if s["iteration"] > s["budgets"]["max_iterations"]:
        block(s, f"budget: max_iterations={s['budgets']['max_iterations']} exhausted")
        sys.exit(1)
    idle = s["iteration"] - s["last_progress_iteration"]
    if idle > NO_PROGRESS_LIMIT:
        block(s, f"no-progress: {idle} iterations without a commit or transition")
        sys.exit(1)
    save(s)
    print(f"ITERATION={s['iteration']} STATE={s['state']} idle={idle}")


def cmd_transition(args: argparse.Namespace) -> None:
    target = args.target.upper()
    if target not in STATES:
        sys.exit(f"Unknown state {target}. States: {', '.join(STATES)}")
    s = load()
    if target not in TRANSITIONS[s["state"]]:
        allowed = ", ".join(sorted(TRANSITIONS[s["state"]])) or "(none)"
        print(f"INVALID {s['state']} → {target}. Allowed: {allowed}")
        sys.exit(2)
    s["history"].append({"at": now(), "to": target, "reason": args.reason})
    s["state"] = target
    s["last_progress_iteration"] = s["iteration"]
    save(s)
    append_progress(f"→ {target}: {args.reason}")
    if target in ("DONE", "BLOCKED") and remove_loop_md():
        # The ritual is over; a bare /loop must now fall through to Claude
        # Code's built-in PR-maintenance prompt instead of re-running us.
        append_progress(f"removed {LOOP_MD_FILE} (bare /loop is free for PR upkeep)")
    print(f"OK {target}")


def cmd_task(args: argparse.Namespace) -> None:
    s = load()
    in_flight = s.get("in_flight", [])
    if args.done:
        if args.task_id in in_flight:
            in_flight.remove(args.task_id)
        if args.task_id in s.get("fix_tasks", []):
            s["fix_tasks"].remove(args.task_id)  # closing a fix task lifts its test-lock
    elif args.task_id not in in_flight:
        in_flight.append(args.task_id)
    s["in_flight"] = in_flight
    s.pop("current_task", None)  # superseded by in_flight (v2.1)
    save(s)
    print(f"OK in_flight=[{', '.join(in_flight) or '-'}]")


def cmd_fix_task(args: argparse.Namespace) -> None:
    """Register (or unlock) a fix task.

    VERIFY and REVIEW create fix tasks for red checks and real findings. While a
    registered fix task is in flight, the test-lock hook denies edits to test
    files, so a green run proves the bug is gone rather than that the test was
    changed (playbook Test stage). The reproducing test is committed *before*
    the task is registered, by the lead, so the lock never blocks it.
    """
    s = load()
    fix = s.setdefault("fix_tasks", [])
    if args.unlock:
        if args.task_id in fix:
            fix.remove(args.task_id)
        save(s)
        append_progress(f"test-lock lifted for {args.task_id}: {args.reason}")
        print(f"OK unlocked {args.task_id} (log a decision explaining why)")
        return
    if args.task_id not in fix:
        fix.append(args.task_id)
    save(s)
    print(
        f"OK fix_tasks=[{', '.join(fix)}] — test files lock while one is in flight "
        f"(task <id> --done lifts it)"
    )


def cmd_gate(args: argparse.Namespace) -> None:
    """Pause at an opt-in approval gate, or print OPEN when it is not configured."""
    s = load()
    name = args.name
    if name not in s.get("gates", []) or name in s.get("gates_passed", []):
        print(f"OPEN {name}")
        return
    if s["state"] not in ACTIVE_STATES:
        sys.exit(f"gate {name}: loop is {s['state']}, nothing to gate.")
    ESCALATION_FILE.write_text(gate_escalation_text(name, s))
    s["history"].append(
        {"at": now(), "to": "BLOCKED", "reason": f"{GATE_REASON_PREFIX}{name}"}
    )
    s["state"] = "BLOCKED"
    s["last_progress_iteration"] = s["iteration"]
    save(s)
    append_progress(f"→ BLOCKED: gate {name} (human review requested; re-run /sdlc)")
    if remove_loop_md():
        append_progress(f"removed {LOOP_MD_FILE} (gate; /sdlc rewrites it)")
    print(f"GATED {name} — loop paused for human review ({ESCALATION_FILE}); stop now")


def cmd_attempt(args: argparse.Namespace) -> None:
    s = load()
    n = s["attempts"].get(args.task_id, 0) + 1
    s["attempts"][args.task_id] = n
    save(s)
    limit = s["budgets"]["max_attempts_per_task"]
    if n > limit:
        print(
            f"EXCEEDED task={args.task_id} attempts={n}/{limit} — mark it blocked and move on"
        )
        sys.exit(1)
    print(f"OK task={args.task_id} attempts={n}/{limit}")


def cmd_decide(args: argparse.Namespace) -> None:
    s = load()
    SDLC_DIR.mkdir(exist_ok=True)
    entry = {
        "at": now(),
        "iteration": s["iteration"],
        "state": s["state"],
        "decision": args.decision,
        "why": args.why,
        "reversible": not args.irreversible,
    }
    with DECISIONS_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print("OK decision logged")


def cmd_set_budget(args: argparse.Namespace) -> None:
    s = load()
    b = s["budgets"]
    changed = []
    for key, value in (
        ("max_iterations", args.max_iterations),
        ("max_attempts_per_task", args.max_attempts),
        ("max_wait_ticks", args.max_wait_ticks),
    ):
        if value is not None:
            b[key] = value
            changed.append(f"{key}={value}")
    if not changed:
        sys.exit("Nothing to set — pass at least one --max-* flag.")
    save(s)
    append_progress(f"budgets adjusted: {', '.join(changed)}")
    print(f"OK {', '.join(changed)}")


def cmd_set_driver(args: argparse.Namespace) -> None:
    s = load()
    s["driver"] = args.driver
    save(s)
    print(f"OK driver={args.driver}")


def cmd_note_progress(args: argparse.Namespace) -> None:
    s = load()
    s["last_progress_iteration"] = s["iteration"]
    save(s)
    append_progress(args.what)
    print("OK")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="create .sdlc/ state (idempotent: resumes)")
    sp.add_argument("--feature", required=True)
    sp.add_argument("--request", default="")
    sp.add_argument("--max-iterations", type=int, default=50)
    sp.add_argument("--max-attempts", type=int, default=3)
    sp.add_argument("--max-wait-ticks", type=int, default=200)
    # auto: the Stop hook drives. /loop is user-armed — if the user arms it and
    # says so, set-driver loop stands the hook down (see DRIVERS).
    sp.add_argument("--driver", choices=list(DRIVERS), default="auto")
    sp.add_argument(
        "--reviewers",
        default=None,
        help=(
            "Comma-separated reviewers run at the REVIEW gate (skills or "
            "pr-review-toolkit agents). Default: code-review."
        ),
    )
    sp.add_argument(
        "--review-mode",
        choices=list(REVIEW_MODES),
        default=None,
        help=(
            "block: findings become fix tasks → BUILD (default). "
            "annotate: findings are listed in the PR body, never block SHIP."
        ),
    )
    sp.add_argument(
        "--intent",
        default=None,
        help=(
            "Path to an existing intent document (the playbook's intent.md). "
            "Omit to record specs/<feature>-intent.md, which INIT writes from the request."
        ),
    )
    sp.add_argument(
        "--gate",
        dest="gates",
        default=None,
        help=(
            "Comma-separated approval gates: plan (pause after the plan commits, "
            "before BUILD) and/or ship (pause before opening the PR). Each pause is "
            "BLOCKED with an escalation file; re-running /sdlc passes the gate."
        ),
    )
    sp.set_defaults(func=cmd_init)

    sub.add_parser("state", help="print just the state name").set_defaults(
        func=cmd_state
    )
    sub.add_parser("status", help="human-readable summary").set_defaults(
        func=cmd_status
    )
    sp = sub.add_parser("tick", help="start an iteration; enforce budgets")
    sp.add_argument(
        "--waiting",
        action="store_true",
        help="wait-check on in-flight agents: not counted against iteration/idle budgets",
    )
    sp.set_defaults(func=cmd_tick)

    sp = sub.add_parser("transition", help="move to a new state")
    sp.add_argument("target")
    sp.add_argument("--reason", required=True)
    sp.set_defaults(func=cmd_transition)

    sp = sub.add_parser("increment", help="finish this increment, start the next")
    sp.add_argument("--feature", required=True)
    sp.add_argument("--request", default="")
    sp.add_argument("--intent", default=None)
    sp.set_defaults(func=cmd_increment)

    sp = sub.add_parser("gate", help="pause at an opt-in approval gate (or print OPEN)")
    sp.add_argument("name", choices=list(GATES))
    sp.set_defaults(func=cmd_gate)

    sp = sub.add_parser(
        "fix-task", help="register a fix task (test files lock while it is in flight)"
    )
    sp.add_argument("task_id")
    sp.add_argument("--unlock", action="store_true", help="lift the test-lock early")
    sp.add_argument("--reason", default="unlocked", help="why the lock was lifted")
    sp.set_defaults(func=cmd_fix_task)

    sp = sub.add_parser("task", help="mark a task in flight (or done with --done)")
    sp.add_argument("task_id")
    sp.add_argument("--done", action="store_true")
    sp.set_defaults(func=cmd_task)

    sp = sub.add_parser("set-budget", help="adjust budgets mid-loop")
    sp.add_argument("--max-iterations", type=int)
    sp.add_argument("--max-attempts", type=int)
    sp.add_argument("--max-wait-ticks", type=int)
    sp.set_defaults(func=cmd_set_budget)

    sp = sub.add_parser("set-driver", help="record the loop driver")
    sp.add_argument("driver", choices=list(DRIVERS))
    sp.set_defaults(func=cmd_set_driver)

    sp = sub.add_parser("attempt", help="count an attempt on a task")
    sp.add_argument("task_id")
    sp.set_defaults(func=cmd_attempt)

    sp = sub.add_parser("decide", help="log an autonomous decision")
    sp.add_argument("--decision", required=True)
    sp.add_argument("--why", required=True)
    sp.add_argument("--irreversible", action="store_true")
    sp.set_defaults(func=cmd_decide)

    sp = sub.add_parser("note-progress", help="record progress (resets idle counter)")
    sp.add_argument("--what", required=True)
    sp.set_defaults(func=cmd_note_progress)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
