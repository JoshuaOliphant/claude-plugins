#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typesafe-sdk>=0.7"]
# ///
# ABOUTME: Independent VERIFY judge: asks Jev whether each acceptance criterion's test evidence shows it is met.
# ABOUTME: Code settles untested and failing criteria; Jev judges the rest; exits 0 only when every AC is met.
"""Usage: uv run ac_judge.py --spec specs/{slug}-spec.md --evidence .sdlc/ac-evidence.json

The evidence file maps each AC id to the tests that exercise it and their result:

    {"AC-1": {"result": "passed", "tests": ["def test_login(): ..."]}}

Exit codes: 0 every AC met, 1 at least one AC not met, 2 judge unavailable,
3 skipped because TYPESAFE_API_KEY is not set.
"""

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from typesafe_sdk import Choice, TypeSafeClient, TypeSafeError

DEFAULT_THRESHOLD = 0.8

AC_START = re.compile(r"^(?:#{1,6}\s*)?AC-(\d+)\b[:.]?\s*(.*)$")
SECTION_START = re.compile(r"^#{1,3}\s")

JUDGMENT_CRITERIA = {
    "supports": (
        "The assertions check every Then outcome the criterion lists, "
        "by driving the behavior its When describes."
    ),
    "partial": (
        "The evidence drives the criterion's behavior, but at least one Then outcome "
        "the criterion lists is never asserted."
    ),
    "contradicts": (
        "An assertion expects an outcome that conflicts with the criterion, "
        "such as a different value, message, limit, or destination."
    ),
    "says_nothing": (
        "The evidence does not exercise the criterion's behavior: it tests something else, "
        "is a stub, or its assertions cannot fail."
    ),
}

JUDGMENT_VERDICTS = {
    "partial": "partial",
    "contradicts": "unmet",
    "says_nothing": "untested",
}


@dataclass(frozen=True)
class AcceptanceCriterion:
    id: str
    text: str


@dataclass(frozen=True)
class Verdict:
    ac_id: str
    verdict: str
    reason: str
    judgment: str | None = None
    confidence: float | None = None
    probabilities: dict[str, float] | None = None


def parse_acceptance_criteria(spec_text: str) -> list[AcceptanceCriterion]:
    criteria = []
    current_id = None
    lines: list[str] = []
    for line in spec_text.splitlines():
        match = AC_START.match(line.strip())
        if match:
            if current_id:
                criteria.append(AcceptanceCriterion(current_id, "\n".join(lines).strip()))
            current_id = f"AC-{match.group(1)}"
            lines = [line.strip()]
        elif current_id and SECTION_START.match(line):
            criteria.append(AcceptanceCriterion(current_id, "\n".join(lines).strip()))
            current_id = None
        elif current_id:
            lines.append(line)
    if current_id:
        criteria.append(AcceptanceCriterion(current_id, "\n".join(lines).strip()))
    return criteria


def state_key(ac_id: str) -> str:
    return ac_id.lower().replace("-", "_")


def settle_without_model(ac: AcceptanceCriterion, evidence: dict) -> Verdict | None:
    entry = evidence.get(ac.id)
    if not entry or not entry.get("tests"):
        return Verdict(ac.id, "untested", "no tests recorded for this criterion")
    if entry.get("result") != "passed":
        return Verdict(ac.id, "unmet", f"tests did not pass (result: {entry.get('result')})")
    return None


def build_question(ac: AcceptanceCriterion) -> Choice:
    key = state_key(ac.id)
    return Choice(
        instructions=(
            f"All tests in `evidence.{key}` passed. Judge whether their assertions demonstrate "
            f"that the acceptance criterion `criteria.{key}` is met. Judge what the assertions "
            f"actually check, not what test names, docstrings, or comments claim."
        ),
        criteria=JUDGMENT_CRITERIA,
    )


def verdict_from_answer(ac_id: str, answer, threshold: float) -> Verdict:
    fields = {
        "judgment": answer.choice,
        "confidence": answer.confidence,
        "probabilities": dict(answer.probabilities),
    }
    if answer.choice != "supports":
        verdict = JUDGMENT_VERDICTS[answer.choice]
        return Verdict(ac_id, verdict, f"Jev judged the evidence: {answer.choice}", **fields)
    if answer.confidence < threshold:
        reason = f"Jev leaned supports below the {threshold} confidence threshold"
        return Verdict(ac_id, "needs_review", reason, **fields)
    return Verdict(ac_id, "met", "Jev judged the evidence supports the criterion", **fields)


def judge(
    criteria: list[AcceptanceCriterion], evidence: dict, client, threshold: float
) -> list[Verdict]:
    settled = {ac.id: settle_without_model(ac, evidence) for ac in criteria}
    pending = [ac for ac in criteria if settled[ac.id] is None]
    if pending:
        state = {
            "criteria": {state_key(ac.id): ac.text for ac in pending},
            "evidence": {state_key(ac.id): evidence[ac.id]["tests"] for ac in pending},
        }
        questions = {state_key(ac.id): build_question(ac) for ac in pending}
        response = client.system_one(state=state, questions=questions)
        for ac in pending:
            answer = response.choices[state_key(ac.id)]
            settled[ac.id] = verdict_from_answer(ac.id, answer, threshold)
    return [settled[ac.id] for ac in criteria]


def format_report(verdicts: list[Verdict]) -> str:
    lines = []
    for v in verdicts:
        confidence = "" if v.confidence is None else f" ({v.confidence:.2f})"
        lines.append(f"{v.ac_id}: {v.verdict}{confidence} — {v.reason}")
    met = sum(v.verdict == "met" for v in verdicts)
    lines.append(f"{met}/{len(verdicts)} acceptance criteria met")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--out", type=Path, help="write verdicts as JSON here")
    args = parser.parse_args(argv)

    if not os.environ.get("TYPESAFE_API_KEY"):
        print("skipped: TYPESAFE_API_KEY is not set")
        return 3

    criteria = parse_acceptance_criteria(args.spec.read_text())
    if not criteria:
        print(f"no AC-N criteria found in {args.spec}")
        return 1
    evidence = json.loads(args.evidence.read_text())

    try:
        with TypeSafeClient() as client:
            verdicts = judge(criteria, evidence, client, args.threshold)
    except TypeSafeError as error:
        print(f"judge unavailable: {error}")
        return 2

    print(format_report(verdicts))
    if args.out:
        args.out.write_text(json.dumps([asdict(v) for v in verdicts], indent=2) + "\n")
    return 0 if all(v.verdict == "met" for v in verdicts) else 1


if __name__ == "__main__":
    sys.exit(main())
