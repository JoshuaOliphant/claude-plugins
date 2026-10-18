#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typesafe-sdk>=0.7.1"]
# ///
# ABOUTME: Mutates claims that compost-evals labels `backed` (cases, hand mutants and results stay in that private repo) and reports, per operator, how often Jev's claim-backed judgment notices.
# ABOUTME: Issue #113 PoC: one Noul (the shipped judge) and one three-way Choice (supports, contradicts, says_nothing) per mutant.
import argparse
import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "plugins" / "compost" / "scripts"))

from typesafe_sdk import Choice  # noqa: E402

from jevtools import testing  # noqa: E402
from jevtools.core import Cache, open_client, session  # noqa: E402

AUTO = 0.8  # the citation-check cookbook's AUTO_ACCEPT: below it a person confirms the verdict
NOUL_CUT = testing.BACKED

RELATION = Choice(
    instructions=(
        "`claim` is a statement from a report about finished work, such as a test count, a coverage figure, or a "
        "clean lint run. `output` is the captured output of the command offered as its evidence; a long output is "
        "clipped in the middle. How does `output` relate to `claim`?"
    ),
    criteria={
        "supports": "The output shows what the claim states, with the same numbers, and shows nothing that the claim denies",
        "contradicts": "The output shows something that conflicts with the claim: a different number, a failure, or the opposite outcome",
        "says_nothing": "The output never shows what the claim is about, so it neither backs nor refutes it",
    },
)
# Variant written after the first run showed `supports` passing claims with an unshown conjunct: it makes "every part" explicit.
RELATION_STRICT = Choice(
    instructions=RELATION.instructions,
    criteria={
        "supports": "Every part of the claim is shown by the output, with the same numbers, and nothing in the output denies any part",
        "contradicts": "The output shows something that conflicts with some part of the claim: a different number, a failure, or the opposite outcome",
        "says_nothing": "Some part of the claim, or all of it, is never shown by the output, and nothing in the output conflicts with it",
    },
)
QUESTIONS = {"backed": testing.OUTPUT_BACKS_CLAIM, "relation": RELATION, "strict": RELATION_STRICT}

NEGATIONS = [
    (r"\bpasses\b", "fails"),
    (r"\bpassed\b", "failed"),
    (r"\bpass\b", "fail"),
    (r"\bclean\b", "full of findings"),
    (r"\bbelow\b", "above"),
]


def number_swap(claim: str, output: str) -> str | None:
    """Bump the last digit of a number the output also shows, so the claim now states a number the output lacks."""
    for match in re.finditer(r"\d+(?:\.\d+)?", claim):
        if match.group(0) not in output:
            continue
        digits = match.group(0)
        bumped = digits[:-1] + str((int(digits[-1]) + 1) % 10)
        if bumped not in output:
            return claim[: match.start()] + bumped + claim[match.end() :]
    return None


def negate(claim: str, output: str) -> str | None:
    for pattern, word in NEGATIONS:
        if re.search(pattern, claim):
            return re.sub(pattern, word, claim, count=1)
    return None


def overclaim(claim: str, output: str) -> str | None:
    """Add a conjunct about a type check, which none of the fixture outputs run."""
    return None if "type" in output.lower() else f"{claim.rstrip('.')} and the type check is clean."


def wrong_subject(claim: str, output: str) -> str | None:
    match = re.search(r"\btest_\w+", claim)
    if not match:
        return None
    swapped = match.group(0) + "_for_empty_input"
    return None if swapped in output else claim.replace(match.group(0), swapped)


OPERATORS = {
    "number-swap": number_swap,
    "negate": negate,
    "overclaim": overclaim,
    "wrong-subject": wrong_subject,
}


PART_SPLIT = re.compile(r"\s+and\s+|;\s+|\s+with\s+|,\s+(?=coverage|\d)")


def parts(claim: str) -> list[str]:
    """Code splits a claim into the pieces it asserts. Written after the first run, on cues seen in these cases, so it is tuned to them."""
    return [part.strip(" .") for part in PART_SPLIT.split(claim) if part.strip(" .")] or [claim]


def numbers_missing(claim: str, output: str) -> bool:
    """The deterministic stage: a number the claim states that the output never shows."""
    return any(n not in output for n in re.findall(r"\d+(?:\.\d+)?", claim))


def load(evals: Path, hand: list[dict]) -> list[dict]:
    spec = json.loads((evals / "claim-backed.json").read_text())
    outputs = {}
    items = []
    for case in spec["cases"]:
        output = (
            case["output"]
            if "output" in case
            else (evals / case["output_file"]).read_text(errors="replace")
        )
        outputs[case["claim"]] = output
        if case["backed"]:
            items.append(
                {"operator": "original", "claim": case["claim"], "output": output, "backed": True}
            )
    for original in [i for i in items if i["operator"] == "original"]:
        for name, make in OPERATORS.items():
            if (claim := make(original["claim"], original["output"])) and claim != original[
                "claim"
            ]:
                items.append(
                    {
                        "operator": name,
                        "claim": claim,
                        "output": original["output"],
                        "backed": False,
                        "from": original["claim"],
                    }
                )
    for entry in hand:
        if entry["from"] in outputs:
            items.append(
                {
                    "operator": entry["operator"],
                    "claim": entry["claim"],
                    "output": outputs[entry["from"]],
                    "backed": entry["backed"],
                    "from": entry["from"],
                }
            )
    return items


async def judge_all(items: list[dict], out: Path) -> None:
    async with session(open_client, Cache(out / "jev-cache.json")) as jev:

        async def one(item: dict) -> None:
            answers = await jev.ask(
                "judge-mutation",
                {"claim": item["claim"], "output": testing.clip(item["output"])},
                QUESTIONS,
            )
            item["noul"] = round(answers.noul("backed"), 3)
            item["relation"] = answers.choice("relation")
            item["confidence"] = round(answers.confidence("relation"), 3)
            item["strict_relation"] = answers.choice("strict")
            item["strict_confidence"] = round(answers.confidence("strict"), 3)
            pieces = parts(item["claim"])
            item["parts"] = len(pieces)
            if (
                len(pieces) == 1
            ):  # one piece is the whole claim, so the split judge's answer is the whole-claim answer
                item["split_noul"] = item["noul"]
                item["split_relation"] = item["strict_relation"]
                item["split_confidence"] = item["strict_confidence"]
                return
            each = await asyncio.gather(
                *(
                    jev.ask(
                        "judge-mutation-part",
                        {"claim": piece, "output": testing.clip(item["output"])},
                        QUESTIONS,
                    )
                    for piece in pieces
                )
            )
            item["split_noul"] = round(min(a.noul("backed") for a in each), 3)
            doubtful = [
                (a.choice("strict"), a.confidence("strict"))
                for a in each
                if a.choice("strict") != "supports"
            ]
            if doubtful:
                item["split_relation"], item["split_confidence"] = max(
                    doubtful, key=lambda pair: pair[1]
                )
            else:
                item["split_relation"], item["split_confidence"] = (
                    "supports",
                    min(a.confidence("strict") for a in each),
                )
            item["split_confidence"] = round(item["split_confidence"], 3)

        await asyncio.gather(*(one(i) for i in items))
        print(f"input tokens {jev.input_tokens}, cached asks {jev.cached}", file=sys.stderr)


def outcome(item: dict, prefix: str = "") -> str:
    """For a claim that should be unbacked: caught, routed to a person, or missed. For one that should stay backed: kept, routed, or flagged."""
    verdict_ok = item[f"{prefix}relation"] == "supports"
    sure = item[f"{prefix}confidence"] >= AUTO
    if item["backed"]:
        return "kept" if verdict_ok and sure else ("routed" if not sure else "flagged")
    return "missed" if verdict_ok and sure else ("routed" if not sure else "caught")


def report(items: list[dict]) -> str:
    by_op = defaultdict(list)
    for item in items:
        by_op[item["operator"]].append(item)
    lines = [
        f"Verdicts on claims that should be unbacked, per operator. Noul cut {NOUL_CUT}. Choice: auto means confidence >= {AUTO},",
        "routed means below it (a person confirms), so caught + routed + missed = n. strict is the Choice with the every-part criteria;",
        "split cuts the claim into parts in code and judges each part (strict Choice; split noul = lowest part).",
        "det = claims stating a number the output never shows (the deterministic stage, no model). noul = claims judged unbacked.",
        "",
        f"{'operator':<19}{'n':>3} {'det':>4} {'noul':>6} | {'choice c/r/m':>13} | {'strict c/r/m':>13} | {'split c/r/m':>12} {'split noul':>10}",
    ]
    for op, rows in by_op.items():
        n = len(rows)
        det = sum(numbers_missing(r["claim"], r["output"]) for r in rows)
        keep = all(r["backed"] for r in rows)
        noul = sum(
            r["noul"] < NOUL_CUT for r in rows
        )  # unbacked verdicts: caught, or false flags on kept rows
        split_noul = sum(r["split_noul"] < NOUL_CUT for r in rows)
        cells = []
        for prefix in ("", "strict_", "split_"):
            o = defaultdict(int)
            for r in rows:
                o[outcome(r, prefix)] += 1
            cells.append(
                f"{o['flagged' if keep else 'caught']}/{o['routed']}/{o['kept' if keep else 'missed']}"
            )
        lines.append(
            f"{op:<19}{n:>3} {det:>4} {noul:>3}/{n:<2} | {cells[0]:>13} | {cells[1]:>13} | {cells[2]:>12} {split_noul:>7}/{n:<2}"
            + ("   (kept rows: flagged/routed/kept)" if keep else "")
        )
    lines += ["", "Not caught or wrongly flagged (choice, strict, split):"]
    for r in items:
        for prefix, label in (("", "choice"), ("strict_", "strict"), ("split_", "split")):
            o = outcome(r, prefix)
            if o in ("missed", "flagged"):
                lines.append(
                    f"  [{r['operator']}/{label}/{o}] noul {r['noul']} {r[prefix + 'relation']} {r[prefix + 'confidence']}  {r['claim'][:100]}"
                )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evals", default=os.environ.get("COMPOST_EVALS"), help="compost-evals' evals/ directory"
    )
    parser.add_argument(
        "--hand", help="hand-written mutants; default <evals>/judge-mutation/hand-mutants.json"
    )
    parser.add_argument("--out", help="results directory; default <evals>/judge-mutation/results")
    args = parser.parse_args()
    evals = Path(args.evals).expanduser()
    out = Path(args.out) if args.out else evals / "judge-mutation" / "results"
    out.mkdir(parents=True, exist_ok=True)
    hand = Path(args.hand) if args.hand else evals / "judge-mutation" / "hand-mutants.json"
    items = load(evals, json.loads(hand.read_text()))
    asyncio.run(judge_all(items, out))
    with (out / "results.jsonl").open("w") as handle:
        for item in items:
            handle.write(json.dumps({k: v for k, v in item.items() if k != "output"}) + "\n")
    text = report(items)
    (out / "analysis.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
