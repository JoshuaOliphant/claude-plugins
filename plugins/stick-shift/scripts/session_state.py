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

    sp = sub.add_parser("transition", help="move to a phase (nudge on off-graph)")
    sp.add_argument("target")
    sp.add_argument("--reason", required=True)
    sp.set_defaults(func=cmd_transition)

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

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
