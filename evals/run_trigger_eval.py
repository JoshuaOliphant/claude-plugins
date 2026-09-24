#!/usr/bin/env python3
# ABOUTME: Trigger-eval fitness function for meta-agent search (docs/meta-agent-search-design.md).
# ABOUTME: Scores a skill description against evals/*-eval.json via an LLM judge, emits METRIC lines.
"""Score skill descriptions against the trigger-eval fixtures.

For each ``{"query": ..., "should_trigger": bool}`` case, an LLM judge (haiku via the
``claude`` CLI) decides whether Claude Code would invoke the skill given only its
name and description. Cases are deterministically split into **dev** (optimized by
the meta-search loop) and **holdout** (read by humans judging whether a win is real);
the primary metric is balanced accuracy, with the false-positive rate reported
separately because an over-triggering skill pollutes unrelated sessions.

Usage:
    python evals/run_trigger_eval.py --skill tdd-workflow            # one skill
    python evals/run_trigger_eval.py --all                           # every mapped skill
    python evals/run_trigger_eval.py --skill tdd-workflow \
        --description-file candidate/SKILL.md                        # candidate genome
    python evals/run_trigger_eval.py --all --judge stub              # plumbing test, no LLM

Output: human-readable table plus autoloop-convention ``METRIC key=value`` lines.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = REPO_ROOT / "evals"

# Maps each eval fixture to the SKILL.md whose description it exercises.
# NOTE: verification-stack-eval.json is deliberately absent — it targeted the
# verification-stack skill that autonomous-sdlc v2 removed in favor of the
# built-in /verify (docs/sdlc-loop-redesign.md §1.4). Kept as a fixture only.
EVAL_TO_SKILL: dict[str, str] = {
    "bdd-generate": "plugins/autonomous-sdlc/skills/bdd-generate/SKILL.md",
    "bdd-spec": "plugins/autonomous-sdlc/skills/bdd-spec/SKILL.md",
    "beads-workflow": "plugins/autonomous-sdlc/skills/beads-workflow/SKILL.md",
    "tdd-workflow": "plugins/autonomous-sdlc/skills/tdd-workflow/SKILL.md",
    "compound-capture": "plugins/compound-knowledge/skills/compound-capture/SKILL.md",
    "compound-retrieve": "plugins/compound-knowledge/skills/compound-retrieve/SKILL.md",
    "hexagonal-agents": "plugins/hexagonal-agents/skills/hexagonal-agents/SKILL.md",
    "mochi-creator": "plugins/mochi-creator/skills/mochi-creator/SKILL.md",
}

DEV_FRACTION = 0.7
JUDGE_MODEL = "claude-haiku-4-5-20251001"
JUDGE_BATCH_SIZE = 10

# Frozen judge prompt: the optimizer must never hold the measuring stick, so any
# edit to this template invalidates cross-run score comparisons.
JUDGE_PROMPT_TEMPLATE = """\
You simulate Claude Code's skill-triggering decision.

A skill is available:
name: {name}
description: {description}

For each numbered user request below, decide whether Claude Code should invoke this
skill for that request. Judge strictly by the description; many requests are
deliberately adjacent but out of scope.

Requests:
{numbered_queries}

Reply with ONLY a JSON array of {n} booleans, one per request, in order. No other text.
"""

Judge = Callable[[str, str, Sequence[str]], list[bool]]


@dataclass
class SplitScores:
    n: int
    balanced_accuracy: float
    tpr: float
    tnr: float
    fp_rate: float


def parse_frontmatter_description(skill_md: str) -> tuple[str, str]:
    """Return (name, description) from a SKILL.md's YAML frontmatter.

    Handles the two styles used in this repo: plain scalars and ``>``/``>-``
    folded blocks. Avoids a YAML dependency so the script runs bare.
    """
    m = re.match(r"\A---\n(.*?)\n---", skill_md, re.S)
    if not m:
        raise ValueError("no YAML frontmatter found")
    lines = m.group(1).split("\n")
    fields: dict[str, str] = {}
    key = None
    buf: list[str] = []
    folded = False
    for line in lines:
        top = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if top:
            if key is not None:
                fields[key] = " ".join(buf).strip()
            key, rest = top.group(1), top.group(2)
            folded = rest in {">", ">-", "|", "|-"}
            buf = [] if folded else [rest]
        elif key is not None and (line.startswith((" ", "\t")) or line == ""):
            buf.append(line.strip())
    if key is not None:
        fields[key] = " ".join(buf).strip()
    if "name" not in fields or "description" not in fields:
        raise ValueError("frontmatter missing name or description")
    return fields["name"], fields["description"]


def split_cases(cases: list[dict]) -> tuple[list[dict], list[dict]]:
    """Deterministic dev/holdout split keyed on the query text.

    Hash-based so the split never depends on file order and survives cases being
    appended; committed nowhere because it is a pure function of the data.
    """
    dev, holdout = [], []
    for case in cases:
        digest = hashlib.sha256(case["query"].encode()).digest()
        (dev if digest[0] / 256 < DEV_FRACTION else holdout).append(case)
    return dev, holdout


def score_split(cases: list[dict], verdicts: list[bool]) -> SplitScores:
    tp = fn = tn = fp = 0
    for case, verdict in zip(cases, verdicts, strict=True):
        if case["should_trigger"]:
            tp, fn = tp + int(verdict), fn + int(not verdict)
        else:
            tn, fp = tn + int(not verdict), fp + int(verdict)
    tpr = tp / (tp + fn) if tp + fn else 1.0
    tnr = tn / (tn + fp) if tn + fp else 1.0
    return SplitScores(
        n=len(cases),
        balanced_accuracy=(tpr + tnr) / 2,
        tpr=tpr,
        tnr=tnr,
        fp_rate=1.0 - tnr,
    )


def parse_judge_reply(reply: str, expected_n: int) -> list[bool]:
    """Extract a JSON array of booleans, tolerating code fences and prose."""
    m = re.search(r"\[[^\[\]]*\]", reply, re.S)
    if not m:
        raise ValueError(f"no JSON array in judge reply: {reply[:200]!r}")
    verdicts = json.loads(m.group(0))
    if len(verdicts) != expected_n or not all(isinstance(v, bool) for v in verdicts):
        raise ValueError(f"expected {expected_n} booleans, got: {verdicts!r}")
    return verdicts


def claude_cli_judge(name: str, description: str, queries: Sequence[str]) -> list[bool]:
    """Judge a batch of queries with one headless haiku call via the claude CLI.

    Runs in a temp cwd so the nested session loads no CLAUDE.md/skills from this
    repo. Retries once on unparseable output.
    """
    numbered = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(queries))
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        name=name, description=description, numbered_queries=numbered, n=len(queries)
    )
    last_error: Exception | None = None
    for _ in range(2):
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", JUDGE_MODEL, "--max-turns", "1"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=tempfile.gettempdir(),
        )
        try:
            return parse_judge_reply(result.stdout, len(queries))
        except (ValueError, json.JSONDecodeError) as e:
            last_error = e
    raise RuntimeError(f"judge failed twice for {name}: {last_error}")


def stub_judge(name: str, description: str, queries: Sequence[str]) -> list[bool]:
    """No-LLM judge for plumbing tests: triggers iff the skill name appears verbatim."""
    return [name.lower() in q.lower() for q in queries]


def judge_all(name: str, description: str, cases: list[dict], judge: Judge) -> list[bool]:
    verdicts: list[bool] = []
    for i in range(0, len(cases), JUDGE_BATCH_SIZE):
        batch = cases[i : i + JUDGE_BATCH_SIZE]
        verdicts.extend(judge(name, description, [c["query"] for c in batch]))
    return verdicts


def evaluate_skill(
    eval_name: str,
    description_file: Path,
    judge: Judge,
    eval_file: Path | None = None,
) -> dict:
    """Evaluate one description against one eval fixture. Returns a result dict."""
    eval_path = eval_file or EVALS_DIR / f"{eval_name}-eval.json"
    cases = json.loads(eval_path.read_text())
    name, description = parse_frontmatter_description(description_file.read_text())
    dev, holdout = split_cases(cases)
    results = {}
    for split_name, split in (("dev", dev), ("holdout", holdout)):
        verdicts = judge_all(name, description, split, judge)
        results[split_name] = score_split(split, verdicts)
    return {
        "eval": eval_name,
        "skill_name": name,
        "description_file": str(description_file),
        "description_words": len(description.split()),
        "dev": vars(results["dev"]),
        "holdout": vars(results["holdout"]),
    }


def emit(result: dict, metric_prefix: str = "") -> None:
    d, h = result["dev"], result["holdout"]
    print(
        f"{result['eval']:>20}  dev {d['balanced_accuracy']:.3f} "
        f"(tpr {d['tpr']:.2f} fp {d['fp_rate']:.2f} n={d['n']})  "
        f"holdout {h['balanced_accuracy']:.3f} "
        f"(tpr {h['tpr']:.2f} fp {h['fp_rate']:.2f} n={h['n']})  "
        f"desc {result['description_words']}w"
    )
    p = f"{metric_prefix}{result['eval']}_"
    print(f"METRIC {p}dev_score={d['balanced_accuracy']:.4f}")
    print(f"METRIC {p}holdout_score={h['balanced_accuracy']:.4f}")
    print(f"METRIC {p}dev_fp_rate={d['fp_rate']:.4f}")
    print(f"METRIC {p}desc_words={result['description_words']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", help="eval name from the mapping (e.g. tdd-workflow)")
    parser.add_argument("--all", action="store_true", help="run every mapped skill")
    parser.add_argument(
        "--description-file",
        type=Path,
        help="SKILL.md to score instead of the committed one (candidate genomes)",
    )
    parser.add_argument("--judge", choices=["haiku", "stub"], default="haiku")
    parser.add_argument("--json", action="store_true", help="also dump full results as JSON")
    args = parser.parse_args(argv)

    if bool(args.skill) == args.all:
        parser.error("exactly one of --skill or --all is required")
    if args.all and args.description_file:
        parser.error("--description-file only makes sense with --skill")

    judge = claude_cli_judge if args.judge == "haiku" else stub_judge
    targets = list(EVAL_TO_SKILL) if args.all else [args.skill]
    results = []
    for eval_name in targets:
        if eval_name not in EVAL_TO_SKILL:
            parser.error(f"unknown skill {eval_name!r}; known: {', '.join(EVAL_TO_SKILL)}")
        description_file = args.description_file or REPO_ROOT / EVAL_TO_SKILL[eval_name]
        results.append(evaluate_skill(eval_name, description_file, judge))
        emit(results[-1])

    if args.json:
        print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
