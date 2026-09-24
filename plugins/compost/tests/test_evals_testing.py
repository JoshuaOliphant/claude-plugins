# ABOUTME: Live evals for the testing family's Jev tools, run against the labeled cases in tests/evals/.
# ABOUTME: Each prints its measurements and a threshold sweep, and asserts a floor measured on 24 Sep 2026.
import asyncio
import json
from pathlib import Path

import pytest
from jevtools import core, suite, testing

pytestmark = pytest.mark.jev

PLUGIN_ROOT = Path(__file__).parent.parent
EVALS = PLUGIN_ROOT / "tests" / "evals"
PRICE_PER_TOKEN = 42 / 1e9


def labeled(name: str) -> dict:
    return json.loads((EVALS / f"{name}.json").read_text())


def fixture_suite(path: str, limit: int) -> dict[str, str]:
    tests: dict[str, str] = {}
    for relative, source in json.loads((PLUGIN_ROOT / path).read_text()).items():
        tests.update(suite.tests_in(relative, source, limit))
    return tests


def live(judge, gathered: dict) -> dict:
    async def run():
        async with core.open_client() as client:
            jev = core.Jev(client, core.Cache())
            result = await judge(jev, gathered)
        print(f"\n{jev.input_tokens} input tokens (~${jev.input_tokens * PRICE_PER_TOKEN:.4f})")
        return result

    return asyncio.run(run())


def rates(scored: list[tuple[float, bool]], threshold: float) -> tuple[float, float, float]:
    flagged = [label for value, label in scored if value >= threshold]
    hits = sum(flagged)
    positives = sum(label for _, label in scored)
    correct = hits + sum(not label for value, label in scored if value < threshold)
    precision = hits / len(flagged) if flagged else 1.0
    return correct / len(scored), precision, hits / positives


def sweep(scored: list[tuple[float, bool]], thresholds: list[float]) -> None:
    print("threshold  accuracy  precision  recall")
    for threshold in thresholds:
        accuracy, precision, recall = rates(scored, threshold)
        print(f"{threshold:9.2f}  {accuracy:8.2f}  {precision:9.2f}  {recall:6.2f}")


TENTHS = [round(0.05 * step, 2) for step in range(1, 20)]


def test_find_test_places_criteria_and_extends_only_covered_ones():
    cases = labeled("find-test")
    rows = []
    for name, path in cases["suites"].items():
        chosen = [case for case in cases["cases"] if case["suite"] == name]
        tests = fixture_suite(path, testing.FULL_SOURCE_CHARS)
        result = live(testing.find_test, {"criteria": [c["criterion"] for c in chosen], "tests": tests})
        rows += zip(chosen, result["placements"], strict=True)
    placed = top3 = 0
    scored = []
    for case, placement in rows:
        right = placement["test"] in case["tests"]
        placed += right
        top3 += bool({placement["test"], *placement["alternatives"]} & set(case["tests"]))
        scored.append((placement["covered"], case["covered"] and right))
        print(
            f"{'ok ' if right else 'MISS'} covered={placement['covered']:.2f} conf={placement['confidence']:.2f} "
            f"label={'covered' if case['covered'] else 'novel  '} {placement['action']:10} {placement['test']}"
        )
    print(f"placement top-1 {placed}/{len(rows)}, top-3 {top3}/{len(rows)}")
    print("extend (the chosen test already covers the criterion) when covered >= threshold:")
    sweep(scored, TENTHS)
    accuracy, precision, recall = rates(scored, testing.EXTEND_COVERED)
    print(
        f"at EXTEND_COVERED={testing.EXTEND_COVERED}: accuracy {accuracy:.2f} precision {precision:.2f} recall {recall:.2f}"
    )
    assert placed >= 0.9 * len(rows)
    assert accuracy >= 0.9 and precision >= 0.9


def source_of(test: dict, cases: dict, suites: dict[str, dict[str, str]]) -> str:
    if "source" in test:
        return test["source"]
    if "source_ref" in test:
        return cases["sources"][test["source_ref"]]
    return suites[test["suite"]][test["test"]]


def test_duplicate_test_separates_re_covered_behavior_from_neighbours():
    cases = labeled("duplicate-test")
    suites = {name: fixture_suite(path, testing.FULL_SOURCE_CHARS) for name, path in cases["suites"].items()}
    changes = [
        {
            "test": case["added"]["test"],
            "status": "added",
            "source": source_of(case["added"], cases, suites),
            "neighbours": [
                {
                    "test": case["existing"]["test"],
                    "source": source_of(case["existing"], cases, suites),
                    "similarity": 0,
                }
            ],
        }
        for case in cases["cases"]
    ]
    result = live(testing.duplicate_test, {"base": "eval", "changes": changes})
    scored = []
    for case, judged in zip(cases["cases"], result["tests"], strict=True):
        same = judged["neighbours"][0]["same_behavior"]
        scored.append((same, case["duplicate"]))
        print(f"{same:.2f} {'dup ' if case['duplicate'] else 'diff'} {case['added']['test']}")
    sweep(scored, TENTHS)
    accuracy, precision, recall = rates(scored, testing.DUPLICATE)
    print(f"at DUPLICATE={testing.DUPLICATE}: accuracy {accuracy:.2f} precision {precision:.2f} recall {recall:.2f}")
    assert accuracy >= 0.85 and precision >= 0.85


def test_ac_exercised_flags_tests_that_never_assert_the_then():
    cases = labeled("ac-exercised")
    suites = {name: fixture_suite(path, testing.FULL_SOURCE_CHARS) for name, path in cases["suites"].items()}
    criteria = [
        testing.mapped(
            {"id": f"AC-{number}", "text": case["criterion"], "test": case["test"]},
            {case["test"].partition("[")[0]: source_of(case, cases, suites)},
        )
        for number, case in enumerate(cases["cases"], 1)
    ]
    result = live(testing.ac_exercised, {"criteria": criteria})
    scored = []
    for case, judged in zip(cases["cases"], result["criteria"], strict=True):
        scored.append((judged["probability"], case["exercised"]))
        print(f"{judged['probability']:.2f} {'yes' if case['exercised'] else 'no '} {case['test']}")
    sweep(scored, TENTHS)
    accuracy, precision, recall = rates(scored, testing.EXERCISED)
    print(f"at EXERCISED={testing.EXERCISED}: accuracy {accuracy:.2f} precision {precision:.2f} recall {recall:.2f}")
    assert accuracy >= 0.85 and precision >= 0.9


def test_test_value_proposes_exclusions_only_for_blocks_that_prove_nothing(tmp_path):
    cases = labeled("test-value")
    for name, text in json.loads((PLUGIN_ROOT / cases["code"]).read_text()).items():
        (tmp_path / name).write_text(text)
    uncovered = [{"file": case["file"], "lines": case["lines"]} for case in cases["cases"]]
    gathered = testing.gather_gaps({"repo": str(tmp_path), "uncovered": uncovered})
    assert len(gathered["gaps"]) == len(cases["cases"])
    result = live(testing.test_value, gathered)
    scored = []
    for case, block in zip(cases["cases"], result["blocks"], strict=True):
        scored.append((block["score"], case["worth"] == "test"))
        print(f"{block['score']:.2f} {case['worth']:7} {case['file']}:{case['lines'][0]}")
    print("a block needs a test when its score >= threshold; recall is the share of real behavior kept:")
    sweep(scored, [step / 4 for step in range(1, 12)])
    accuracy, precision, recall = rates(scored, testing.EXCLUDE_BELOW)
    print(
        f"at EXCLUDE_BELOW={testing.EXCLUDE_BELOW}: accuracy {accuracy:.2f} precision {precision:.2f} recall {recall:.2f}"
    )
    assert accuracy >= 0.85 and recall >= 0.9


def test_claim_backed_checks_claims_against_their_output():
    cases = labeled("claim-backed")
    claims = [
        {"claim": case["claim"], "output_file": str(PLUGIN_ROOT / case["output_file"])}
        if "output_file" in case
        else {"claim": case["claim"], "output": case["output"]}
        for case in cases["cases"]
    ]
    result = live(testing.claim_backed, testing.gather_claims({"claims": claims}))
    scored = []
    for case, judged in zip(cases["cases"], result["claims"], strict=True):
        scored.append((judged["probability"], case["backed"]))
        print(f"{judged['probability']:.2f} {'yes' if case['backed'] else 'no '} {case['claim']}")
    sweep(scored, TENTHS)
    accuracy, precision, recall = rates(scored, testing.BACKED)
    print(f"at BACKED={testing.BACKED}: accuracy {accuracy:.2f} precision {precision:.2f} recall {recall:.2f}")
    assert accuracy >= 0.85 and precision >= 0.9
