#!/usr/bin/env python3
# ABOUTME: State machine CLI for the autonomous-sdlc loop.
# ABOUTME: Owns .sdlc/state.json — transitions, budgets, decisions, progress.
"""SDLC loop state machine.

Every loop iteration starts by calling `tick` and ends by calling
`transition` or `note-progress`. The goal evaluator (or the fallback Stop
hook) calls `state` to decide whether the loop may exit. All state lives in
.sdlc/ in the current working directory so any fresh context can resume.

Usage:
    sdlc_state.py init --feature user-auth --request "Add auth" [--max-iterations 50]
    sdlc_state.py state                    # prints just the state name (for evaluators)
    sdlc_state.py status                   # human-readable summary
    sdlc_state.py tick                     # start an iteration: bump counter, enforce budgets
    sdlc_state.py transition BUILD --reason "plan committed, 6 tasks ready"
    sdlc_state.py task bd-a1b2             # set current task
    sdlc_state.py attempt bd-a1b2          # count an attempt; exit 1 when budget exceeded
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
        print(f"RESUME state={state['state']} iteration={state['iteration']}")
        return
    SDLC_DIR.mkdir(exist_ok=True)
    state = {
        "feature": args.feature,
        "request": args.request,
        "state": "INIT",
        "driver": args.driver,
        "iteration": 0,
        "budgets": {
            "max_iterations": args.max_iterations,
            "max_attempts_per_task": args.max_attempts,
        },
        "current_task": None,
        "attempts": {},
        "last_progress_iteration": 0,
        "history": [{"at": now(), "to": "INIT", "reason": "initialized"}],
        "started": now(),
    }
    save(state)
    if not PROGRESS_FILE.exists():
        PROGRESS_FILE.write_text(
            f"# Progress: {args.feature}\n\nRequest: {args.request}\n\n"
        )
    append_progress(f"loop initialized (driver={args.driver})")
    print(f"INIT feature={args.feature} driver={args.driver}")


def cmd_state(_args: argparse.Namespace) -> None:
    print(load()["state"])


def cmd_status(_args: argparse.Namespace) -> None:
    s = load()
    b = s["budgets"]
    print(f"STATE={s['state']}")
    print(f"feature: {s['feature']}")
    print(f"iteration: {s['iteration']}/{b['max_iterations']}")
    print(f"current task: {s['current_task'] or '-'}")
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
    print(f"BLOCKED {reason}")


def cmd_tick(_args: argparse.Namespace) -> None:
    s = load()
    if s["state"] in ("DONE", "BLOCKED"):
        print(s["state"])
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
    print(f"OK {target}")


def cmd_task(args: argparse.Namespace) -> None:
    s = load()
    s["current_task"] = args.task_id
    save(s)
    print(f"OK current_task={args.task_id}")


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
    sp.add_argument("--driver", choices=["goal", "stop-hook"], default="goal")
    sp.set_defaults(func=cmd_init)

    sub.add_parser("state", help="print just the state name").set_defaults(
        func=cmd_state
    )
    sub.add_parser("status", help="human-readable summary").set_defaults(
        func=cmd_status
    )
    sub.add_parser("tick", help="start an iteration; enforce budgets").set_defaults(
        func=cmd_tick
    )

    sp = sub.add_parser("transition", help="move to a new state")
    sp.add_argument("target")
    sp.add_argument("--reason", required=True)
    sp.set_defaults(func=cmd_transition)

    sp = sub.add_parser("task", help="set the current task")
    sp.add_argument("task_id")
    sp.set_defaults(func=cmd_task)

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
