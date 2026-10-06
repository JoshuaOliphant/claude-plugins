# ABOUTME: Live eval for the skill-drift mod's Jev questions on 60 labeled real skill-turns in compost-evals (COMPOST_EVALS).
# ABOUTME: Asks each question as hooks/skill-drift.ts does, prints a threshold sweep, and asserts the floor measured 6 Oct 2026.
import asyncio
import json

import pytest
from conftest import TENTHS, evals_dir, rates, skill_drift_judgments, sweep
from jevtools import core
from typesafe_sdk import Noul

pytestmark = pytest.mark.jev


def scored_by_question() -> dict[str, list[tuple[float, bool]]]:
    judgments = skill_drift_judgments()
    turn_questions = {name: Noul(instructions=text) for name, text in judgments["turn"].items()}
    next_questions = {name: Noul(instructions=text) for name, text in judgments["next_message"].items()}
    cases = json.loads((evals_dir() / "skill-drift.json").read_text())

    async def judge(jev: core.Jev, case: dict) -> dict:
        state = case["state"]
        turn = {"skill": state["skill"], "turn": state["turn"]}
        answered = await asyncio.gather(
            jev.ask("skill-drift", turn, turn_questions),
            jev.ask("skill-drift", {**turn, "next_user_message": state["next_user_message"]}, next_questions),
        )
        return {name: answer["noul"] for answers in answered for name, answer in answers.items()}

    async def run() -> list[dict]:
        async with core.open_client() as client:
            jev = core.Jev(client, core.Cache())
            results = await asyncio.gather(*(judge(jev, case) for case in cases))
        print(f"\n{jev.input_tokens} input tokens over {len(cases)} cases")
        return results

    results = asyncio.run(run())
    return {
        name: [(result[name], case["expected"][name]) for case, result in zip(cases, results, strict=True)]
        for name in judgments["thresholds"]
    }


def test_each_question_flags_its_labeled_drift_at_the_mods_threshold():
    thresholds = skill_drift_judgments()["thresholds"]
    scored = scored_by_question()
    measured = {}
    for name, rows in scored.items():
        print(f"\n{name}: {sum(label for _, label in rows)} positives of {len(rows)}")
        sweep(rows, TENTHS)
        measured[name] = rates(rows, thresholds[name])
    for name, (accuracy, precision, recall) in measured.items():
        print(f"{name} at {thresholds[name]}: accuracy {accuracy:.2f} precision {precision:.2f} recall {recall:.2f}")
    deviated_precision, deviated_recall = measured["deviated"][1:]
    assert deviated_precision >= 0.75 and deviated_recall >= 0.9
    assert measured["missing_guidance"][2] == measured["corrected"][2] == 1.0
