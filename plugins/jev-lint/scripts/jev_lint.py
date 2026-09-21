#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typesafe-sdk>=0.7"]
# ///
# ABOUTME: Semantic linter for Python: asks Jev plain-language questions about comments, handlers, functions, logs, and diffs.
# ABOUTME: One request per unit carries every rule that applies to it; findings at or above the threshold are reported.
"""Usage: uv run jev_lint.py [PATH ...] [--diff REF] [--rules id,id] [--threshold 0.5] [--json]

Exit codes: 0 no findings, 1 findings reported, 2 Jev unavailable,
3 skipped because TYPESAFE_API_KEY is not set.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from extract import Unit, extract_hunks, extract_source_units
from rules import RULES, Rule
from typesafe_sdk import AsyncTypeSafeClient, TypeSafeError

DEFAULT_THRESHOLD = 0.5
DEFAULT_CONCURRENCY = 16
SKIPPED_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".git", "build", "dist"}


@dataclass(frozen=True)
class Judgment:
    path: str
    line: int
    name: str
    rule: str
    label: str
    probability: float
    message: str


def python_files(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_file():
            files.append(path)
            continue
        for candidate in sorted(path.rglob("*.py")):
            parts = candidate.relative_to(path).parts
            if not any(part in SKIPPED_DIRS or part.startswith(".") for part in parts[:-1]):
                files.append(candidate)
    return files


def collect_units(paths: list[Path]) -> list[Unit]:
    units = []
    for path in python_files(paths):
        try:
            units.extend(extract_source_units(str(path), path.read_text()))
        except (SyntaxError, UnicodeDecodeError) as error:
            print(f"skipped {path}: {error}", file=sys.stderr)
    return units


def git_diff(ref: str) -> str:
    return subprocess.run(
        ["git", "diff", "-U3", ref, "--", "*.py"], check=True, capture_output=True, text=True
    ).stdout


def select_rules(ids: str | None) -> list[Rule]:
    if not ids:
        return RULES
    wanted = {rule_id.strip() for rule_id in ids.split(",")}
    unknown = wanted - {rule.id for rule in RULES}
    if unknown:
        raise ValueError(f"unknown rules: {', '.join(sorted(unknown))}")
    return [rule for rule in RULES if rule.id in wanted]


async def judge_unit(client, semaphore, unit: Unit, rules: list[Rule]) -> list[Judgment]:
    applicable = [rule for rule in rules if rule.kind == unit.kind and rule.applies(unit)]
    if not applicable:
        return []
    async with semaphore:
        response = await client.system_one(
            state=unit.state, questions={rule.id: rule.question for rule in applicable}
        )
    judgments = []
    for rule in applicable:
        probability, label = rule.probability(response.answers[rule.id])
        judgments.append(
            Judgment(unit.path, unit.line, unit.name, rule.id, label, probability, rule.message)
        )
    return judgments


async def judge_units(client, units: list[Unit], rules: list[Rule], concurrency: int):
    semaphore = asyncio.Semaphore(concurrency)
    batches = await asyncio.gather(*(judge_unit(client, semaphore, u, rules) for u in units))
    return [judgment for batch in batches for judgment in batch]


def format_finding(judgment: Judgment) -> str:
    return (
        f"{judgment.path}:{judgment.line}: {judgment.rule} "
        f"[{judgment.label} p={judgment.probability:.2f}] {judgment.message} ({judgment.name})"
    )


async def run(units: list[Unit], rules: list[Rule], concurrency: int) -> list[Judgment]:
    async with AsyncTypeSafeClient() as client:
        return await judge_units(client, units, rules, concurrency)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--diff", metavar="REF", help="also judge hunks of `git diff REF`")
    parser.add_argument("--rules", help="comma-separated rule ids (default: all)")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--json", action="store_true", help="print every judgment as JSON")
    args = parser.parse_args(argv)

    if not os.environ.get("TYPESAFE_API_KEY"):
        print("skipped: TYPESAFE_API_KEY is not set")
        return 3

    try:
        rules = select_rules(args.rules)
    except ValueError as error:
        parser.error(str(error))
    units = collect_units(args.paths if args.paths or args.diff else [Path(".")])
    if args.diff:
        units.extend(extract_hunks(git_diff(args.diff)))

    try:
        judgments = asyncio.run(run(units, rules, args.concurrency))
    except TypeSafeError as error:
        print(f"jev unavailable: {error}")
        return 2

    findings = sorted(
        (j for j in judgments if j.probability >= args.threshold),
        key=lambda j: -j.probability,
    )
    if args.json:
        print(json.dumps([asdict(j) for j in judgments], indent=2))
    else:
        for finding in findings:
            print(format_finding(finding))
        print(f"{len(findings)} findings from {len(judgments)} judgments over {len(units)} units")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
