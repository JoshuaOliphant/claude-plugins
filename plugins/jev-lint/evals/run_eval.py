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
    return unit


def comment_cases(path: Path) -> list[tuple[Unit, bool, str]]:
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
        cases.append((unit, record["label"] == "deleted", f"{record['repo']}@{record['sha']}"))
    return cases


async def judge(
    labeled: list[tuple[Unit, bool, str, str]],
) -> list[tuple[str, bool, float, str, str]]:
    keys = Counter((unit.path, unit.line) for unit, *_ in labeled)
    duplicated = [key for key, count in keys.items() if count > 1]
    if duplicated:
        raise ValueError(f"labeled units share a path and line: {duplicated[:3]}")
    by_rule = defaultdict(list)
    for unit, flag, source, rule_id in labeled:
        by_rule[rule_id].append((unit, flag, source))
    results = []
    for rule_id, cases in by_rule.items():
        units = [unit for unit, _, _ in cases]
        judgments, failures = await run(units, [RULES_BY_ID[rule_id]], concurrency=16)
        if failures:
            failed = [f"{f.unit.path}:{f.unit.line}: {f.error}" for f in failures]
            raise RuntimeError(f"Jev failed on {len(failures)} {rule_id} cases: {failed[:3]}")
        by_unit = {(j.path, j.line): j for j in judgments}
        for unit, flag, source in cases:
            judgment = by_unit[(unit.path, unit.line)]
            results.append((rule_id, flag, judgment.probability, judgment.label, source))
    return results


def report(results) -> None:
    by_rule = defaultdict(list)
    for rule_id, flag, probability, label, source in results:
        by_rule[rule_id].append((flag, probability, label, source))
    for rule_id, rows in by_rule.items():
        positives = sum(flag for flag, *_ in rows)
        print(f"\n== {rule_id}: {len(rows)} cases, {positives} should flag ==")
        for threshold in THRESHOLDS:
            flagged = [(flag, p) for flag, p, *_ in rows if p >= threshold]
            true_positives = sum(flag for flag, _ in flagged)
            precision = true_positives / len(flagged) if flagged else float("nan")
            recall = true_positives / positives if positives else float("nan")
            print(
                f"  threshold {threshold}: flagged {len(flagged):3}  "
                f"precision {precision:.2f}  recall {recall:.2f}"
            )
        misses = [row for row in rows if (row[1] >= 0.5) != row[0]]
        for flag, probability, label, source in misses[:12]:
            kind = "missed" if flag else "false alarm"
            print(f"    {kind:11} p={probability:.2f} [{label}] {source}")


def main() -> None:
    labeled = []
    for index, case in enumerate(CASES):
        unit = unit_for_case(index, case)
        unit = Unit(unit.kind, f"case{index}/{unit.path}", unit.line, unit.name, unit.state)
        snippet = (case.get("source") or case["diff"]).strip().splitlines()
        source = snippet[0] if "source" in case else snippet[-1]
        labeled.append((unit, case["flag"], source[:70], case["rule"]))
    if len(sys.argv) > 1:
        comments_path = Path(sys.argv[1])
        if not comments_path.exists():
            sys.exit(f"no such comments file: {comments_path}")
        for unit, flag, source in comment_cases(comments_path):
            labeled.append((unit, flag, f"{source} {unit.name}", "comment-kind"))

    start = time.perf_counter()
    results = asyncio.run(judge(labeled))
    elapsed = time.perf_counter() - start
    report(results)
    print(f"\n{len(results)} judgments in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
