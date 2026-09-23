#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typesafe-sdk>=0.7"]
# ///
# ABOUTME: Semantic linter for Python: asks Jev plain-language questions about comments, handlers, functions, logs, and diffs.
# ABOUTME: One request per unit carries every rule that applies to it; findings at or above each rule's threshold are reported.
"""Usage: uv run jev_lint.py [PATH ...] [--diff REF] [--rules id,id] [--threshold P]
                         [--concurrency N] [--json]

Exit codes: 0 no findings, 1 findings reported, 2 Jev failed for at least one unit,
3 skipped because TYPESAFE_API_KEY is not set, 4 bad input (missing path, git diff
failure, unreadable files, or nothing to lint).
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from extract import Unit, extract_hunks, extract_source_units
from rules import RULES, Rule
from typesafe_sdk import AsyncTypeSafeClient, TypeSafeError

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_JEV_FAILED = 2
EXIT_NO_KEY = 3
EXIT_BAD_INPUT = 4
DEFAULT_CONCURRENCY = 16
SKIPPED_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".git", "build", "dist"}


class MissingAnswer(Exception):
    pass


class GitDiffError(Exception):
    pass


@dataclass(frozen=True)
class Judgment:
    path: str
    line: int
    name: str
    rule: str
    label: str
    probability: float
    message: str
    static_rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class Failure:
    unit: Unit
    error: str


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
    return list(dict.fromkeys(files))


def collect_units(paths: list[Path]) -> tuple[list[Unit], list[str]]:
    units, skipped = [], []
    for path in python_files(paths):
        try:
            units.extend(extract_source_units(str(path), path.read_text()))
        except (SyntaxError, UnicodeDecodeError, OSError) as error:
            skipped.append(f"{path}: {error}")
    return units, skipped


def git_diff(ref: str) -> str:
    try:
        return subprocess.run(
            ["git", "diff", "-U3", ref, "--", "*.py"], check=True, capture_output=True, text=True
        ).stdout
    except subprocess.CalledProcessError as error:
        raise GitDiffError(error.stderr.strip() or f"git diff {ref} exited {error.returncode}")


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
        if rule.id not in response.answers:
            raise MissingAnswer(f"Jev returned no answer for {rule.id}")
        probability, label = rule.probability(response.answers[rule.id])
        judgments.append(
            Judgment(
                unit.path,
                unit.line,
                unit.name,
                rule.id,
                label,
                probability,
                rule.message_for(label),
                rule.static_equivalents(label, unit),
            )
        )
    return judgments


async def judge_units(
    client, units: list[Unit], rules: list[Rule], concurrency: int
) -> tuple[list[Judgment], list[Failure]]:
    semaphore = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(
        *(judge_unit(client, semaphore, unit, rules) for unit in units), return_exceptions=True
    )
    judgments, failures = [], []
    for unit, result in zip(units, results):
        if isinstance(result, (TypeSafeError, MissingAnswer)):
            failures.append(Failure(unit, str(result)))
        elif isinstance(result, BaseException):
            raise result
        else:
            judgments.extend(result)
    return judgments, failures


def format_finding(judgment: Judgment) -> str:
    line = (
        f"{judgment.path}:{judgment.line}: {judgment.rule} "
        f"[{judgment.label} p={judgment.probability:.2f}] {judgment.message} ({judgment.name})"
    )
    if judgment.static_rules:
        line += f" [ruff: {', '.join(judgment.static_rules)}]"
    return line


def static_rule_summary(findings: list[Judgment]) -> list[str]:
    counts = Counter(code for finding in findings for code in finding.static_rules)
    if not counts:
        return []
    lines = [
        "Syntactic findings ruff can catch without Jev; add to [tool.ruff.lint] extend-select:"
    ]
    for code, count in counts.most_common():
        lines.append(f"  {code}: {count} finding{'s' if count != 1 else ''}")
    return lines


def summary_line(findings, judgments, units, skipped, failures) -> str:
    line = f"{len(findings)} findings from {len(judgments)} judgments over {len(units)} units"
    if skipped:
        line += f"; {len(skipped)} files skipped"
    if failures:
        line += f"; {len(failures)} units failed"
    return line


async def run(units: list[Unit], rules: list[Rule], concurrency: int):
    async with AsyncTypeSafeClient() as client:
        return await judge_units(client, units, rules, concurrency)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--diff", metavar="REF", help="also judge hunks of `git diff REF`")
    parser.add_argument("--rules", help="comma-separated rule ids (default: all)")
    parser.add_argument(
        "--threshold", type=float, help="flag at or above this probability (default: per rule)"
    )
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--json", action="store_true", help="print every judgment as JSON")
    args = parser.parse_args(argv)

    try:
        rules = select_rules(args.rules)
    except ValueError as error:
        parser.error(str(error))
    missing = [path for path in args.paths if not path.exists()]
    if missing:
        for path in missing:
            print(f"no such path: {path}", file=sys.stderr)
        return EXIT_BAD_INPUT
    if not os.environ.get("TYPESAFE_API_KEY"):
        print("skipped: TYPESAFE_API_KEY is not set")
        return EXIT_NO_KEY

    units, skipped = collect_units(args.paths if args.paths or args.diff else [Path(".")])
    if args.diff:
        try:
            units.extend(extract_hunks(git_diff(args.diff)))
        except GitDiffError as error:
            print(f"git diff failed: {error}", file=sys.stderr)
            return EXIT_BAD_INPUT
    if not units and not skipped:
        print("nothing to lint: no Python units found", file=sys.stderr)
        return EXIT_BAD_INPUT

    try:
        judgments, failures = asyncio.run(run(units, rules, args.concurrency))
    except TypeSafeError as error:
        print(f"jev unavailable: {error}", file=sys.stderr)
        return EXIT_JEV_FAILED

    thresholds = {
        rule.id: rule.threshold if args.threshold is None else args.threshold for rule in rules
    }
    findings = sorted(
        (j for j in judgments if j.probability >= thresholds[j.rule]),
        key=lambda j: -j.probability,
    )
    if args.json:
        print(json.dumps([asdict(j) for j in judgments], indent=2))
    else:
        for finding in findings:
            print(format_finding(finding))
        for line in static_rule_summary(findings):
            print(line)
        print(summary_line(findings, judgments, units, skipped, failures))
    for entry in skipped:
        print(f"skipped {entry}", file=sys.stderr)
    for failure in failures:
        unit = failure.unit
        print(
            f"jev failed on {unit.path}:{unit.line} ({unit.name}): {failure.error}", file=sys.stderr
        )

    if failures:
        return EXIT_JEV_FAILED
    if skipped:
        return EXIT_BAD_INPUT
    return EXIT_FINDINGS if findings else EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
