# ABOUTME: Live evals for the spec family's Jev tools against labeled cases in compost-evals (COMPOST_EVALS) (pytest -m jev).
# ABOUTME: Each prints its accuracy, precision, and recall and asserts the floor measured when its threshold was set.
import asyncio
import json

import jev
import pytest
from conftest import evals_dir
from jevtools.core import Unavailable

pytestmark = pytest.mark.jev


def cases(name: str) -> list[dict]:
    return json.loads((evals_dir() / f"{name}.json").read_text())


def live(tool: str, payload: dict) -> dict:
    try:
        return asyncio.run(jev.run(tool, payload))
    except Unavailable as error:
        pytest.skip(str(error))


def report(tool: str, predicted: list[bool], expected: list[bool], output: dict) -> float:
    pairs = list(zip(predicted, expected, strict=True))
    hits = sum(p == e for p, e in pairs)
    true_positives = sum(p and e for p, e in pairs)
    precision = true_positives / max(sum(predicted), 1)
    recall = true_positives / max(sum(expected), 1)
    accuracy = hits / len(pairs)
    print(
        f"\n{tool}: accuracy {hits}/{len(pairs)} = {accuracy:.2f}, precision {precision:.2f}, recall {recall:.2f}, "
        f"input tokens {output['jev']['input_tokens']}"
    )
    return accuracy


def test_spec_class():
    labeled = cases("spec-class")
    output = live("spec-class", {"requests": [{"request": c["request"], "survey": c["survey"]} for c in labeled]})
    results = output["classifications"]
    for case, result in zip(labeled, results, strict=True):
        print(case["expected"], result["class"], result["jev_pick"], result["confidence"], case["request"][:60])
    correct = sum(r["class"] == c["expected"] for c, r in zip(labeled, results, strict=True))
    print(f"\nspec-class: {correct}/{len(labeled)}, input tokens {output['jev']['input_tokens']}")
    too_light = [
        r
        for c, r in zip(labeled, results, strict=True)
        if r["class"] != c["expected"] and c["expected"] == "architectural"
    ]
    assert correct / len(labeled) >= 0.9
    assert not too_light


def test_question_value():
    predicted, expected, tokens = [], [], 0
    for group in cases("question-value"):
        payload = {"request": group["request"], "questions": group["questions"]}
        output = live("question-value", payload)
        tokens += output["jev"]["input_tokens"]
        decisions = {q["id"]: q for q in output["questions"]}
        for number, question in enumerate(group["questions"], start=1):
            scored = decisions[f"Q{number}"]
            print(question["ask"], scored["decision"], scored["value"], question["question"][:60])
            predicted.append(scored["decision"] != "assume")
            expected.append(question["ask"])
    assert report("question-value", predicted, expected, {"jev": {"input_tokens": tokens}}) >= 0.9


def test_ac_quality():
    labeled = cases("ac-quality")
    output = live("ac-quality", {"criteria": [c["text"] for c in labeled]})
    results = output["criteria"]
    for case, result in zip(labeled, results, strict=True):
        scores = [result[name] for name in ("observable_then", "specific_given", "single_behavior")]
        print(case["rewrite"], result["rewrite"], result["combined"], scores, case["text"][:50])
    predicted = [r["rewrite"] for r in results]
    assert report("ac-quality", predicted, [c["rewrite"] for c in labeled], output) >= 0.9


def test_adr_worthy():
    labeled = cases("adr-worthy")
    output = live("adr-worthy", {"rulings": [c["ruling"] for c in labeled]})
    results = output["rulings"]
    for case, result in zip(labeled, results, strict=True):
        tests = [result[name] for name in ("hard_to_reverse", "surprising", "trade_off")]
        print(case["offer_adr"], result["offer_adr"], tests, case["ruling"]["what"][:60])
    predicted = [r["offer_adr"] for r in results]
    assert report("adr-worthy", predicted, [c["offer_adr"] for c in labeled], output) >= 0.9
