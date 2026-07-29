#!/usr/bin/env python3
# ABOUTME: Retro CLI over the autonomous-sdlc run ledger (~/.claude/autonomous-sdlc).
# ABOUTME: `digest` aggregates runs since the last retro marker; `mark` records a retro point.
"""Aggregate the run ledger for /sdlc-retro.

The loop archives every terminal run (sdlc_state.py archive_run) into a
user-level ledger. This CLI turns that ledger into the digest the sdlc-retro
skill reasons over: score windows per plugin version, outcome and rework
aggregates, and pointers to the worst runs' archived traces. It computes; the
skill (and the human reviewing its PR) interpret.

Usage:
    python3 sdlc_retro.py digest [--all] [--worst N]
    python3 sdlc_retro.py mark --note "<one-line retro summary>"
"""

import argparse
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Minimum runs on BOTH sides before a version-window comparison means anything
# (docs/aflow-sdlc-optimization.md §6).
MIN_WINDOW_N = 5


def runs_root() -> Path:
    env = os.environ.get("SDLC_RUNS_DIR")
    return Path(env) if env else Path.home() / ".claude" / "autonomous-sdlc"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_ledger(root: Path) -> list[dict]:
    ledger_file = root / "runs.jsonl"
    if not ledger_file.exists():
        return []
    records = []
    for line in ledger_file.read_text().splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except ValueError:
            print(f"WARN skipping corrupt ledger line: {line[:80]}", file=sys.stderr)
    return records


def load_marker(root: Path) -> dict | None:
    marker_file = root / "retro.json"
    if not marker_file.exists():
        return None
    try:
        return json.loads(marker_file.read_text())
    except ValueError:
        print("WARN retro.json is corrupt; treating as no marker", file=sys.stderr)
        return None


def window_stats(scores: list[float]) -> dict:
    n = len(scores)
    mean = sum(scores) / n
    var = sum((x - mean) ** 2 for x in scores) / n
    stderr = math.sqrt(var / n) if n > 1 else 0.0
    return {
        "n": n,
        "mean": round(mean, 3),
        # Pessimistic score: what comparisons should use, so an n=1 fluke
        # never displaces an established window.
        "pessimistic": round(mean - stderr, 3),
        "min": round(min(scores), 3),
        "max": round(max(scores), 3),
        "comparable": n >= MIN_WINDOW_N,
    }


def cmd_digest(args: argparse.Namespace) -> None:
    root = runs_root()
    ledger = load_ledger(root)
    marker = load_marker(root)
    since = 0 if (args.all or marker is None) else marker.get("ledger_lines", 0)
    window = ledger[since:]

    digest: dict = {
        "ledger_total": len(ledger),
        "runs": len(window),
        "since_last_retro": not args.all and marker is not None,
        "previous_retro": marker,
    }
    if not window:
        print(json.dumps(digest, indent=2))
        return

    scores = [r["score"] for r in window]
    outcomes = Counter(r["outcome"] for r in window)
    blocked_reasons = Counter(
        r.get("terminal_reason", "?") for r in window if r["outcome"] == "BLOCKED"
    )
    rework_totals: Counter = Counter()
    for r in window:
        rework_totals.update(r.get("rework", {}))
    by_version: dict[str, list[float]] = defaultdict(list)
    for r in window:
        by_version[r.get("plugin_version", "unknown")].append(r["score"])

    digest.update(
        {
            "score": window_stats(scores),
            "outcomes": dict(outcomes),
            "blocked_reasons": dict(blocked_reasons.most_common()),
            "rework_totals": dict(rework_totals),
            "attempts_exceeded_total": sum(
                r.get("attempts_exceeded", 0) for r in window
            ),
            # Whole-ledger view so a retro can grade its predecessor even when
            # the pre-change runs fall outside the current window.
            "by_plugin_version": {
                v: window_stats(s)
                for v, s in sorted(
                    ((v, [r["score"] for r in ledger if r.get("plugin_version") == v])
                     for v in {r.get("plugin_version", "unknown") for r in ledger}),
                )
            },
            "worst_runs": [
                {
                    "at": r["at"],
                    "repo": r.get("repo"),
                    "feature": r.get("feature"),
                    "score": r["score"],
                    "outcome": r["outcome"],
                    "terminal_reason": r.get("terminal_reason"),
                    "archive": r.get("archive"),
                }
                for r in sorted(window, key=lambda r: r["score"])[: args.worst]
            ],
        }
    )
    print(json.dumps(digest, indent=2))


def cmd_mark(args: argparse.Namespace) -> None:
    root = runs_root()
    root.mkdir(parents=True, exist_ok=True)
    ledger = load_ledger(root)
    marker = {
        "at": now(),
        "ledger_lines": len(ledger),
        "plugin_version": (
            ledger[-1].get("plugin_version", "unknown") if ledger else "unknown"
        ),
        "note": args.note,
    }
    (root / "retro.json").write_text(json.dumps(marker, indent=2) + "\n")
    with (root / "retros.jsonl").open("a") as f:
        f.write(json.dumps(marker) + "\n")
    print(f"OK retro marked at ledger line {marker['ledger_lines']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("digest", help="aggregate runs since the last retro marker")
    sp.add_argument("--all", action="store_true", help="ignore the retro marker")
    sp.add_argument("--worst", type=int, default=3, help="worst runs to surface")
    sp.set_defaults(func=cmd_digest)

    sp = sub.add_parser("mark", help="record that a retro ran (windows the next one)")
    sp.add_argument("--note", required=True, help="one-line summary of the retro")
    sp.set_defaults(func=cmd_mark)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
