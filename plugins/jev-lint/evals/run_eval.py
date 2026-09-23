#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typesafe-sdk>=0.7"]
# ///
# ABOUTME: Scores every jev-lint rule against labeled cases on the live Jev API: precision and recall per threshold.
# ABOUTME: Comment cases come from a JSONL of comments that cleanup commits deleted or kept; the rest from cases.py.

import asyncio
import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.path.insert(0, str(HERE))

from cases import CASES
from extract import Unit, extract_hunks, extract_source_units
from jev_lint import run
from rules import RULES

RULES_BY_ID = {rule.id: rule for rule in RULES}
THRESHOLDS = (0.5, 0.7, 0.9)


@dataclass(frozen=True)
class LabeledCase:
    unit: Unit
    should_flag: bool
    source: str
    rule_id: str


@dataclass(frozen=True)
class Scored:
    rule_id: str
    should_flag: bool
    probability: float
    label: str
    source: str


def unit_for_case(index: int, case: dict) -> Unit:
    rule = RULES_BY_ID[case["rule"]]
    if "diff" in case:
        units = extract_hunks(case["diff"])
    else:
        path = "tests/test_example.py" if rule.id == "test-smell" else "app/example.py"
        units = extract_source_units(path, case["source"])
    unit = next((u for u in units if u.kind == rule.kind and rule.applies(u)), None)
    if unit is None:
        raise ValueError(
            f"case {index} ({rule.id}) contains no {rule.kind} unit the rule applies to"
        )
    return Unit(unit.kind, f"case{index}/{unit.path}", unit.line, unit.name, unit.state)


def comment_cases(path: Path) -> list[LabeledCase]:
    cases = []
    for line in path.read_text().splitlines():
        record = json.loads(line)
        state = {
            "comment": record["comment"],
            "code_before": record["context_before"],
            "code_after": record["context_after"],
        }
        unit_path = f"{record['label']}/{record['repo']}@{record['sha']}/{record['path']}"
        unit = Unit("comment", unit_path, record["line"], record["comment"][:60], state)
        source = f"{record['repo']}@{record['sha']} {unit.name}"
        cases.append(LabeledCase(unit, record["label"] == "deleted", source, "comment-kind"))
    return cases


async def judge(cases: list[LabeledCase]) -> list[Scored]:
    keys = Counter((case.unit.path, case.unit.line) for case in cases)
    duplicated = [key for key, count in keys.items() if count > 1]
    if duplicated:
        raise ValueError(f"labeled units share a path and line: {duplicated[:3]}")
    by_rule = defaultdict(list)
    for case in cases:
        by_rule[case.rule_id].append(case)
    scored = []
    for rule_id, rule_cases in by_rule.items():
        units = [case.unit for case in rule_cases]
        judgments, failures = await run(units, [RULES_BY_ID[rule_id]], concurrency=16)
        if failures:
            failed = [f"{f.unit.path}:{f.unit.line}: {f.error}" for f in failures]
            raise RuntimeError(f"Jev failed on {len(failures)} {rule_id} cases: {failed[:3]}")
        by_unit = {(j.path, j.line): j for j in judgments}
        for case in rule_cases:
            judgment = by_unit[(case.unit.path, case.unit.line)]
            scored.append(
                Scored(rule_id, case.should_flag, judgment.probability, judgment.label, case.source)
            )
    return scored


def report(scored: list[Scored]) -> None:
    by_rule = defaultdict(list)
    for row in scored:
        by_rule[row.rule_id].append(row)
    for rule_id, rows in by_rule.items():
        positives = sum(row.should_flag for row in rows)
        print(f"\n== {rule_id}: {len(rows)} cases, {positives} should flag ==")
        for threshold in THRESHOLDS:
            flagged = [row for row in rows if row.probability >= threshold]
            true_positives = sum(row.should_flag for row in flagged)
            precision = true_positives / len(flagged) if flagged else float("nan")
            recall = true_positives / positives if positives else float("nan")
            print(
                f"  threshold {threshold}: flagged {len(flagged):3}  "
                f"precision {precision:.2f}  recall {recall:.2f}"
            )
        misses = [row for row in rows if (row.probability >= 0.5) != row.should_flag]
        for row in misses[:12]:
            kind = "missed" if row.should_flag else "false alarm"
            print(f"    {kind:11} p={row.probability:.2f} [{row.label}] {row.source}")


def main() -> None:
    cases = []
    for index, case in enumerate(CASES):
        snippet = (case.get("source") or case["diff"]).strip().splitlines()
        source = snippet[0] if "source" in case else snippet[-1]
        cases.append(
            LabeledCase(unit_for_case(index, case), case["flag"], source[:70], case["rule"])
        )
    if len(sys.argv) > 1:
        comments_path = Path(sys.argv[1])
        if not comments_path.exists():
            sys.exit(f"no such comments file: {comments_path}")
        cases.extend(comment_cases(comments_path))

    start = time.perf_counter()
    scored = asyncio.run(judge(cases))
    elapsed = time.perf_counter() - start
    report(scored)
    print(f"\n{len(scored)} judgments in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
