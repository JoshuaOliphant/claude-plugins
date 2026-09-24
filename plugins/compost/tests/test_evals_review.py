# ABOUTME: Live evals for the review Jev tools against labeled cases in tests/evals/ (real findings, commits, and files
# ABOUTME: from this repo). Marked jev, so they only run with `pytest -m jev`; each prints its measurements and asserts a floor.
import asyncio
import json
from collections import defaultdict

import jev
import pytest
from conftest import PLUGIN_ROOT
from jevtools import review

pytestmark = pytest.mark.jev

EVALS = PLUGIN_ROOT / "tests" / "evals"
REPO = PLUGIN_ROOT.parent.parent


def cases(name: str) -> list[dict]:
    return json.loads((EVALS / f"{name}.json").read_text())["cases"]


def run(name: str, payload: dict) -> dict:
    result = asyncio.run(jev.run(name, payload))
    print(f"{name}: {result['jev']['input_tokens']} input tokens")
    return result


def test_triage_finding_sends_serious_findings_to_a_skeptic():
    labeled = cases("triage-finding")
    findings = [{key: case[key] for key in ("file", "line", "claim", "evidence", "hunk")} for case in labeled]
    triaged = run("triage-finding", {"findings": findings})["findings"]
    exact = sum(case["severity"] == got["severity"] for case, got in zip(labeled, triaged, strict=True))
    serious = [got for case, got in zip(labeled, triaged, strict=True) if case["severity"] in ("blocker", "major")]
    light = [got for case, got in zip(labeled, triaged, strict=True) if case["severity"] not in ("blocker", "major")]
    for case, got in zip(labeled, triaged, strict=True):
        p = got["probabilities"]
        print(
            f"{case['severity']:>13} -> {got['severity']:<13} serious={p['blocker'] + p['major']:.2f} "
            f"conf={got['confidence']:.2f} skeptic={got['worth_skeptic']}  {case['claim'][:60]}"
        )
    caught = sum(got["worth_skeptic"] for got in serious)
    spared = sum(not got["worth_skeptic"] for got in light)
    print(
        f"exact severity {exact}/{len(labeled)}; serious sent to a skeptic {caught}/{len(serious)}; "
        f"minor or not-a-finding spared one {spared}/{len(light)}"
    )
    assert caught / len(serious) >= 0.9
    assert spared / len(light) >= 0.6


def test_review_risk_flags_structural_files():
    labeled = cases("review-risk")
    by_range = defaultdict(list)
    for case in labeled:
        by_range[(case["base"], case["head"])].append(case)
    scored = []
    for (base, head), group in by_range.items():
        files = {
            entry["file"]: entry
            for entry in run("review-risk", {"repo": str(REPO), "base": base, "head": head})["files"]
        }
        scored.extend((case, files[case["file"]]) for case in group)
    for case, got in sorted(scored, key=lambda pair: pair[1]["score"]):
        print(f"level {case['level']} structural={case['structural']!s:5} score={got['score']:.2f}  {case['file']}")
    right = sum(case["structural"] == got["structural"] for case, got in scored)
    flagged = [case for case, got in scored if got["structural"]]
    structural = [case for case, _ in scored if case["structural"]]
    precision = sum(case["structural"] for case in flagged) / max(len(flagged), 1)
    recall = sum(got["structural"] for case, got in scored if case["structural"]) / len(structural)
    print(f"accuracy {right}/{len(scored)}; precision {precision:.2f}; recall {recall:.2f} at {review.STRUCTURAL}")
    assert right / len(scored) >= 0.8


def test_canon_pick_loads_the_essays_a_reviewer_needs():
    labeled = cases("canon-pick")
    picked_total = relevant_picked = relevant_total = quiet = negatives = 0
    for case in labeled:
        result = run("canon-pick", {"summary": case["summary"]})
        picked = {pick["essay"].removesuffix(".md") for pick in result["essays"]}
        relevant = set(case["relevant"])
        top = list(result["probabilities"].items())[:4]
        print(f"want {sorted(relevant)} got {sorted(picked)} top {top}")
        picked_total += len(picked)
        relevant_picked += len(picked & relevant)
        relevant_total += len(relevant)
        if not relevant:
            negatives += 1
            quiet += not picked
    precision = relevant_picked / max(picked_total, 1)
    recall = relevant_picked / relevant_total
    print(
        f"precision {precision:.2f}; recall {recall:.2f}; negatives with no pick {quiet}/{negatives} at {review.CANON_PICK}"
    )
    assert precision >= 0.5
    assert recall >= 0.5


def test_locate_anchors_claims_and_spots_absent_ones():
    labeled = cases("locate")
    queries = [{key: case[key] for key in ("claim", "file", "start", "end") if key in case} for case in labeled]
    located = run("locate", {"repo": str(PLUGIN_ROOT), "queries": queries})["locations"]
    positives = [(case, got) for case, got in zip(labeled, located, strict=True) if case["lines"]]
    negatives = [(case, got) for case, got in zip(labeled, located, strict=True) if not case["lines"]]
    for case, got in zip(labeled, located, strict=True):
        hit = got["line"] in case["lines"]
        print(
            f"want {case['lines']} got {got['line']} hit={hit} p={got['probability']:.2f} exists={got['exists']:.2f}  "
            f"{case['claim'][:60]}"
        )
    anchored = sum(got["line"] in case["lines"] for case, got in positives)
    found = sum(got["found"] for _, got in positives)
    absent = sum(not got["found"] for _, got in negatives)
    print(
        f"anchored {anchored}/{len(positives)}; found {found}/{len(positives)}; "
        f"absent called absent {absent}/{len(negatives)} at {review.FOUND}"
    )
    assert anchored / len(positives) >= 0.85
    assert absent / len(negatives) >= 0.85
