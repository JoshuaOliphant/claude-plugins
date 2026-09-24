# ABOUTME: Tests the spec family's Jev tools (spec-class, question-value, ac-quality, adr-worthy): input checks,
# ABOUTME: and the policy code applies to Jev's answers, at the edges of each threshold.
import asyncio

import pytest
from conftest import StubJev, noul, score
from jevtools import spec
from jevtools.registry import BadInput


def ranked_choice(first: str, confidence: float, second: str) -> dict:
    third = next(name for name in spec.CLASSES if name not in (first, second))
    probabilities = {first: confidence, second: (1 - confidence) * 0.8, third: (1 - confidence) * 0.2}
    return {"type": "choice", "choice": first, "probabilities": probabilities, "confidence": confidence}


@pytest.mark.parametrize(
    ("payload", "requests"),
    [
        ({"request": "add a flag", "survey": "cli.py"}, [{"request": "add a flag", "survey": "cli.py"}]),
        ({"requests": ["a", "b"], "survey": "s"}, [{"request": "a", "survey": "s"}, {"request": "b", "survey": "s"}]),
        ({"requests": [{"request": "a"}]}, [{"request": "a", "survey": ""}]),
    ],
    ids=["one request", "strings share the survey", "dicts carry their own"],
)
def test_gather_requests_accepts_one_or_many(payload, requests):
    assert spec.gather_requests(payload) == {"requests": requests}


@pytest.mark.parametrize(
    ("gather", "payload", "message"),
    [
        (spec.gather_requests, {}, "needs `request` or a non-empty `requests` list"),
        (spec.gather_requests, {"requests": "not a list"}, "non-empty `requests` list"),
        (spec.gather_requests, {"requests": [{"survey": "x"}]}, "each request needs a non-empty `request`"),
        (spec.gather_questions, {"questions": ["q"]}, "input needs a non-empty `request`"),
        (spec.gather_questions, {"request": "r", "questions": [{"options": []}]}, "each question needs"),
        (spec.gather_criteria, {"criteria": ["  "]}, "each criterion needs a non-empty `text`"),
        (spec.gather_rulings, {"rulings": [{"why": "x"}]}, "each ruling needs a non-empty `what`"),
    ],
)
def test_gather_rejects_bad_input(gather, payload, message):
    with pytest.raises(BadInput, match=message):
        gather(payload)


@pytest.mark.parametrize(
    ("pick", "confidence", "runner_up", "chosen"),
    [
        ("bounded", 0.9, "architectural", "bounded"),
        ("bounded", spec.CLASS_CONFIDENCE, "architectural", "bounded"),
        ("bounded", 0.6, "architectural", "architectural"),
        ("spike", 0.5, "bounded", "bounded"),
        ("architectural", 0.5, "bounded", "architectural"),
    ],
    ids=["confident", "at the threshold", "unsure takes heavier", "spike or bounded", "already heaviest"],
)
def test_spec_class_takes_the_heavier_class_when_unsure(pick, confidence, runner_up, chosen):
    jev = StubJev(lambda tool, state, questions: {"class": ranked_choice(pick, confidence, runner_up)})
    gathered = spec.gather_requests({"request": "r", "survey": "s"})
    [result] = asyncio.run(spec.spec_class(jev, gathered))["classifications"]
    assert (result["class"], result["jev_pick"], result["heavier_if_unsure"]) == (chosen, pick, chosen != pick)
    assert jev.calls[0][1] == {"request": "r", "survey": "s"}
    assert list(jev.calls[0][2]["class"].criteria) == ["spike", "bounded", "architectural"]


def valued(*values: float):
    def answer(tool, state, questions):
        return {name: score(values[int(name[1:])]) for name in questions}

    return answer


def test_question_value_asks_the_most_valuable_frontier_questions_up_to_the_round_size():
    edge = spec.ASK_VALUE
    questions = [
        {"question": "cosmetic", "options": ["a", "b"]},
        {"question": "scope", "options": ["in", "out"]},
        {"question": "blocked", "frontier": False},
        {"question": "behavior"},
        {"id": "custom", "question": "at the cut"},
        "fourth valuable",
    ]
    gathered = spec.gather_questions({"request": "r", "questions": questions, "round_size": 2})
    jev = StubJev(valued(0.4, 2.9, 3.0, 2.2, edge, 2.0))
    result = asyncio.run(spec.question_value(jev, gathered))
    decisions = {q["id"]: q["decision"] for q in result["questions"]}
    assert result["round"] == ["Q2", "Q4"]
    assert decisions == {
        "Q1": "assume",
        "Q2": "ask",
        "Q3": "later",
        "Q4": "ask",
        "custom": "next-round",
        "Q6": "next-round",
    }
    assert [q["id"] for q in result["questions"]] == ["Q2", "Q4", "Q6", "custom", "Q1", "Q3"]
    _tool, state, asked = jev.calls[0]
    assert state["questions"][0] == {"question": "cosmetic", "options": ["a", "b"]}
    assert len(asked["q5"].criteria) == len(spec.VALUE_LEVELS) and "`questions[5]`" in asked["q5"].instructions


def test_question_value_round_defaults_to_five():
    gathered = spec.gather_questions({"request": "r", "question": "one"})
    assert gathered["round_size"] == spec.ROUND_SIZE == 5


def graded(then: float, given: float, single: float):
    def answer(tool, state, questions):
        return {
            "observable_then": score(then, 3),
            "specific_given": score(given, 3),
            "single_behavior": score(single, 3),
        }

    return answer


@pytest.mark.parametrize(
    ("then", "rewrite"),
    [(2 * spec.REWRITE_BELOW, False), (2 * spec.REWRITE_BELOW - 0.01, True), (0.0, True)],
    ids=["weakest at the threshold", "weakest just below", "untestable Then"],
)
def test_ac_quality_rewrites_a_criterion_whose_weakest_dimension_is_below_the_threshold(then, rewrite):
    gathered = spec.gather_criteria({"criteria": ["When x, Then y", {"id": "AC-9", "text": "Given a, When b, Then c"}]})
    result = asyncio.run(spec.ac_quality(StubJev(graded(then, 2.0, 1.8)), gathered))
    first, second = result["criteria"]
    assert (first["id"], second["id"]) == ("AC-1", "AC-9")
    assert first["observable_then"] == round(then / 2, 3)
    assert (first["specific_given"], first["single_behavior"]) == (1.0, 0.9)
    assert (first["weakest"], first["combined"], first["rewrite"]) == ("observable_then", round(then / 2, 3), rewrite)


@pytest.mark.parametrize(
    ("tests", "offer"),
    [
        ((0.9, 0.8, 0.85), True),
        (tuple(spec.ADR_THRESHOLDS.values()), True),
        ((spec.ADR_THRESHOLDS["hard_to_reverse"] - 0.01, 0.9, 0.9), False),
        ((0.9, spec.ADR_THRESHOLDS["surprising"] - 0.01, 0.9), False),
        ((0.9, 0.9, spec.ADR_THRESHOLDS["trade_off"] - 0.01), False),
    ],
    ids=["all three clear", "each at its threshold", "easy to reverse", "unsurprising", "no real trade-off"],
)
def test_adr_worthy_offers_an_adr_only_when_all_three_clear(tests, offer):
    names = list(spec.ADR_TESTS)
    jev = StubJev(lambda tool, state, questions: {name: noul(p) for name, p in zip(names, tests, strict=True)})
    gathered = spec.gather_rulings({"ruling": "Use GitHub issues, not beads"})
    [result] = asyncio.run(spec.adr_worthy(jev, gathered))["rulings"]
    assert result == {
        "what": "Use GitHub issues, not beads",
        **dict(zip(names, tests, strict=True)),
        "offer_adr": offer,
    }
    assert jev.calls[0][1] == {"ruling": {"what": "Use GitHub issues, not beads"}}
