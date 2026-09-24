# ABOUTME: Live evals for the meta family's Jev tools on labeled real cases in compost-evals (COMPOST_EVALS) (run with pytest -m jev).
# ABOUTME: Each prints what it measured and asserts the floor measured when its threshold constant was chosen.
import asyncio
import json

import pytest
from conftest import evals_dir
from jevtools import core, meta

pytestmark = pytest.mark.jev


def cases(name: str) -> list[dict]:
    return json.loads((evals_dir() / f"{name}.json").read_text())


def ask_live(judge, gathered: list[dict]) -> list:
    async def run():
        async with core.open_client() as client:
            jev = core.Jev(client, core.Cache())
            results = await asyncio.gather(*(judge(jev, one) for one in gathered))
        print(f"\ninput tokens: {jev.input_tokens}")
        return results

    return asyncio.run(run())


def test_classify_change_sends_every_adopt_and_adapt_to_be_read():
    labeled = cases("classify-change")
    by_source: dict[str, list[dict]] = {}
    for case in labeled:
        change = {"path": case["path"], "skills": case["skills"], "diff": (evals_dir() / case["diff"]).read_text()}
        by_source.setdefault(case["source"], []).append(change)
    gathered = [meta.describe_changes(source, changes) for source, changes in by_source.items()]
    results = ask_live(meta.classify_change, gathered)
    decided = {(result["source"], change["path"]): change for result in results for change in result["changes"]}
    rows = [(case, decided[(case["source"], case["path"])]) for case in labeled]
    for case, change in rows:
        probabilities = " ".join(f"{name}={value:.2f}" for name, value in change["probabilities"].items())
        mark = "ok  " if change["verdict"] == case["expected"] else "MISS"
        print(
            f"{mark} {case['expected']:6} -> {change['verdict']:6} read={change['needs_reading']!s:5} "
            f"{probabilities}  {case['path']}"
        )
    correct = sum(change["verdict"] == case["expected"] for case, change in rows)
    taken = [change for case, change in rows if case["expected"] != "ignore"]
    recorded = [case for case, change in rows if not change["needs_reading"]]
    ignores = [case for case in labeled if case["expected"] == "ignore"]
    print(
        f"accuracy {correct}/{len(rows)}; adopt/adapt sent to reading {sum(c['needs_reading'] for c in taken)}"
        f"/{len(taken)}; ignores recorded without reading {len(recorded)}/{len(ignores)}"
    )
    assert all(change["needs_reading"] for change in taken)
    assert all(case["expected"] == "ignore" for case in recorded)
    assert len(recorded) >= 13


def test_route_sends_real_prompts_to_an_acceptable_skill():
    labeled = cases("route")
    gathered = meta.gather_route({"prompts": [case["prompt"] for case in labeled]})
    [result] = ask_live(meta.route, [gathered])
    hits = 0
    for case, routed in zip(labeled, result["routes"], strict=True):
        hit = routed["skill"] in case["expected"]
        hits += hit
        print(
            f"{'ok  ' if hit else 'MISS'} {routed['skill']:9} margin={routed['margin']:.2f} "
            f"expected={','.join(case['expected'])}  {case['prompt'][:70]!r}"
        )
    print(f"routed {hits}/{len(labeled)} to an acceptable skill")
    assert hits >= 27


def test_rulings_lint_flags_known_drift_and_spares_compost_text():
    labeled = cases("rulings-lint")
    units = [meta.passage(case["file"], case["line"], case["heading"], case["text"]) for case in labeled]
    scores = ask_live(meta.lint, units)
    for case, score in zip(labeled, scores, strict=True):
        if score["gate"] >= 0.3 or "unallowed_stop" in case["violates"]:
            print(
                f"stop? {'unallowed_stop' in case['violates']!s:5} gate={score['gate']:.2f} "
                f"allowed={score['allowed']:.2f} score={score['unallowed_stop']:.2f}  {case['file']}:{case['line']}"
            )
    for rule in meta.RULE_NAMES:
        positives = [score[rule] for case, score in zip(labeled, scores, strict=True) if rule in case["violates"]]
        negatives = sorted(
            (score[rule], case["file"])
            for case, score in zip(labeled, scores, strict=True)
            if rule not in case["violates"]
        )[-3:]
        flagged = [case for case, score in zip(labeled, scores, strict=True) if score[rule] >= meta.FLAG_AT[rule]]
        true = sum(rule in case["violates"] for case in flagged)
        print(
            f"{rule:15} at {meta.FLAG_AT[rule]}: {true}/{len(positives)} caught, {len(flagged) - true} false flags; "
            f"positives {[round(p, 2) for p in positives]}; top negatives "
            f"{[(round(s, 2), f) for s, f in negatives]}"
        )
    caught = sum(
        score[rule] >= meta.FLAG_AT[rule]
        for case, score in zip(labeled, scores, strict=True)
        for rule in case["violates"]
    )
    false_flags = sum(
        score[rule] >= meta.FLAG_AT[rule]
        for case, score in zip(labeled, scores, strict=True)
        for rule in meta.RULE_NAMES
        if rule not in case["violates"]
    )
    wanted = sum(len(case["violates"]) for case in labeled)
    print(f"caught {caught}/{wanted}; false flags {false_flags}")
    assert caught >= wanted - 3
    assert false_flags <= 4


def test_stop_guard_blocks_questions_and_lets_allowed_stops_through():
    labeled = cases("stop-guard")
    results = ask_live(meta.stop_guard, [meta.gather_stop({"message": case["message"]}) for case in labeled])
    for case, result in zip(labeled, results, strict=True):
        mark = "ok  " if result["block"] == case["block"] else "MISS"
        print(
            f"{mark} block={case['block']!s:5} score={result['score']:.2f} waits={result['waits']:.2f} "
            f"allowed={result['allowed']:.2f}  {case['source']}"
        )
    wrong_blocks = [
        case for case, result in zip(labeled, results, strict=True) if result["block"] and not case["block"]
    ]
    missed = [case for case, result in zip(labeled, results, strict=True) if case["block"] and not result["block"]]
    print(f"wrongly blocked {len(wrong_blocks)}; missed {len(missed)} of {sum(c['block'] for c in labeled)}")
    assert wrong_blocks == []
    assert len(missed) <= 1
