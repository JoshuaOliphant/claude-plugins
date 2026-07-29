#!/usr/bin/env python3
# ABOUTME: State machine CLI for the autonomous-sdlc loop.
# ABOUTME: Owns .sdlc/state.json — transitions, budgets, decisions, progress.
"""SDLC loop state machine.

Every loop iteration starts by calling `tick` and ends by calling
`transition` or `note-progress`. The loop driver (the plugin's Stop hook,
or a user-armed /goal evaluator) reads `state` to decide whether the loop
may exit. All state lives in
.sdlc/ in the current working directory so any fresh context can resume.

Usage:
    sdlc_state.py init --feature user-auth --request "Add auth" [--max-iterations 50]
                       [--reviewers code-review,security-review] [--review-mode block]
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
    sdlc_state.py set-driver goal          # record that the user armed /goal (stands the hook down)
    sdlc_state.py decide --decision "JWT RS256 over HS256" --why "..." [--irreversible]
    sdlc_state.py note-progress --what "closed bd-a1b2"
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SDLC_DIR = Path(".sdlc")
STATE_FILE = SDLC_DIR / "state.json"
DECISIONS_FILE = SDLC_DIR / "decisions.jsonl"
PROGRESS_FILE = SDLC_DIR / "progress.md"
SIGNS_FILE = SDLC_DIR / "signs.md"
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


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Run capture + scoring (docs/aflow-sdlc-optimization.md §§3-4) ------------
#
# Every run that reaches a terminal state (DONE or BLOCKED, including budget
# force-blocks) archives its full trace to a durable user-level ledger instead
# of throwing it away. The ledger is what /sdlc-retro periodically mines to
# propose improvements to the skill itself.

# v1 heuristic: a task typically costs ~3 iterations (build + its share of
# verify/review). Tune only after sanity-checking a dozen real ledger records
# against human judgment of "that run went well".
BASELINE_ITERATIONS_PER_TASK = 3.0


def runs_root() -> Path:
    """User-level, cross-project archive. SDLC_RUNS_DIR overrides (tests)."""
    env = os.environ.get("SDLC_RUNS_DIR")
    return Path(env) if env else Path.home() / ".claude" / "autonomous-sdlc"


def plugin_version() -> str:
    """The installed plugin's version — attributes ledger scores to the exact
    skill version that produced them, so a retro can measure its predecessor."""
    manifest = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
    try:
        return json.loads(manifest.read_text())["version"]
    except (OSError, ValueError, KeyError):
        return "unknown"


def current_increment_history(state: dict) -> list[dict]:
    """History entries for the current increment: from its INIT entry on.
    Earlier increments were archived at their own terminal transition."""
    hist = state["history"]
    start = 0
    for i, h in enumerate(hist):
        if h["to"] == "INIT":
            start = i
    return hist[start:]


def compute_score(state: dict) -> dict:
    """Composite run score from the transition trace. Weights per the design
    note: outcome dominates; efficiency, rework, and autonomy split the rest."""
    states = [h["to"] for h in current_increment_history(state)]
    pairs = list(zip(states, states[1:]))
    rework = {
        "verify_bounces": pairs.count(("VERIFY", "BUILD")),
        "review_roundtrips": pairs.count(("REVIEW", "BUILD")),
        "replans": pairs.count(("PLAN", "PLAN")),
        "repairs": states.count("REPAIR"),
    }
    rework_rate = min(sum(rework.values()) / max(len(pairs), 1), 1.0)

    attempts = state.get("attempts", {})
    tasks = max(len(attempts), 1)
    limit = state["budgets"]["max_attempts_per_task"]
    attempts_exceeded = sum(1 for n in attempts.values() if n > limit)

    iterations = state.get("iteration", 0)
    per_task = iterations / tasks
    efficiency = (
        1.0
        if per_task <= BASELINE_ITERATIONS_PER_TASK
        else BASELINE_ITERATIONS_PER_TASK / per_task
    )
    outcome = 1.0 if state["state"] == "DONE" else 0.0
    autonomy = 1.0 - min(attempts_exceeded / tasks, 1.0)
    score = (
        0.5 * outcome
        + 0.2 * efficiency
        + 0.2 * (1.0 - rework_rate)
        + 0.1 * autonomy
    )
    return {
        "score": round(score, 3),
        "outcome": state["state"],
        "iterations": iterations,
        "tasks_attempted": len(attempts),
        "attempts_exceeded": attempts_exceeded,
        "rework": rework,
        "rework_rate": round(rework_rate, 3),
        "wait_ticks": state.get("wait_ticks", 0),
    }


def archive_run(state: dict, reason: str) -> None:
    """Copy the run's trace files into the archive and append a ledger line.

    Best-effort by design: the terminal transition must succeed even when
    archiving cannot (read-only home, weird cwd), so failures only warn.
    """
    try:
        root = runs_root()
        stamp = now().replace(":", "-").replace("+00-00", "Z")
        slug = f"{stamp}_{Path.cwd().name}_{state['feature']}".replace("/", "-")
        run_dir = root / "runs" / slug
        suffix = 1
        while run_dir.exists():
            suffix += 1
            run_dir = root / "runs" / f"{slug}-{suffix}"
        run_dir.mkdir(parents=True)
        for f in (STATE_FILE, DECISIONS_FILE, PROGRESS_FILE, SIGNS_FILE, ESCALATION_FILE):
            if f.exists():
                shutil.copy2(f, run_dir / f.name)
        signs_active = 0
        if SIGNS_FILE.exists():
            signs_active = sum(
                1
                for line in SIGNS_FILE.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            )
        decisions = (
            len(DECISIONS_FILE.read_text().splitlines())
            if DECISIONS_FILE.exists()
            else 0
        )
        record = {
            "at": now(),
            "repo": Path.cwd().name,
            "feature": state["feature"],
            "cycle": state.get("cycle", 1),
            "plugin_version": plugin_version(),
            "terminal_reason": reason,
            "decisions": decisions,
            "signs_active": signs_active,
            "archive": str(run_dir),
            **compute_score(state),
        }
        with (root / "runs.jsonl").open("a") as f:
            f.write(json.dumps(record) + "\n")
        print(f"ARCHIVED {run_dir}")
    except Exception as e:  # noqa: BLE001 — never let archiving break the loop
        print(f"WARN archive failed: {e}", file=sys.stderr)


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
        # A finished (DONE) loop re-invoked with a *new* feature is the next
        # increment, not a resume: archive the finished increment and reset to
        # INIT so a plain `/sdlc "new thing"` works in the same project instead
        # of silently resuming DONE and dropping the new request. Same feature
        # on DONE is a true no-op resume; a non-DONE state always resumes live
        # work untouched (never increment over a loop still in flight).
        if state["state"] == "DONE" and args.feature != state["feature"]:
            apply_increment(state, args.feature, args.request)
            save(state)
            append_progress(
                f"━━ increment {state['cycle']}: {args.feature} — {args.request}"
            )
            print(f"INCREMENT cycle={state['cycle']} feature={args.feature} state=INIT")
            return
        print(f"RESUME state={state['state']} iteration={state['iteration']}")
        return
    SDLC_DIR.mkdir(exist_ok=True)
    state = {
        "feature": args.feature,
        "request": args.request,
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
    append_progress(f"loop initialized (driver={args.driver})")
    print(f"INIT feature={args.feature} driver={args.driver}")


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
    archive_run(state, reason)
    print(f"BLOCKED {reason}")


def apply_increment(state: dict, feature: str, request: str) -> None:
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
    apply_increment(s, args.feature, args.request)
    save(s)
    append_progress(f"━━ increment {s['cycle']}: {args.feature} — {args.request}")
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
    if target in ("DONE", "BLOCKED"):
        archive_run(s, args.reason)
    print(f"OK {target}")


def cmd_task(args: argparse.Namespace) -> None:
    s = load()
    in_flight = s.get("in_flight", [])
    if args.done:
        if args.task_id in in_flight:
            in_flight.remove(args.task_id)
    elif args.task_id not in in_flight:
        in_flight.append(args.task_id)
    s["in_flight"] = in_flight
    s.pop("current_task", None)  # superseded by in_flight (v2.1)
    save(s)
    print(f"OK in_flight=[{', '.join(in_flight) or '-'}]")


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


def cmd_score(_args: argparse.Namespace) -> None:
    print(json.dumps(compute_score(load()), indent=2))


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
    # auto: the Stop hook drives. /goal is user-only — if the user arms it and
    # says so, set-driver goal stands the hook down. The hook drives whenever the
    # driver is not "goal".
    sp.add_argument("--driver", choices=["auto", "goal", "stop-hook"], default="auto")
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
    sp.set_defaults(func=cmd_increment)

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
    sp.add_argument("driver", choices=["auto", "goal", "stop-hook"])
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

    sub.add_parser(
        "score", help="composite run score computed from the transition trace"
    ).set_defaults(func=cmd_score)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
