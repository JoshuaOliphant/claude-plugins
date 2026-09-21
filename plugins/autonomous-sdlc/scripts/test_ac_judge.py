# ABOUTME: Tests for ac_judge.py, the Jev-backed VERIFY spec-compliance judge.
# ABOUTME: A stand-in client returns real SDK ChoiceAnswer objects; the live API is covered by evals/ac_judge.
"""Run from the plugin directory: `uv run --group dev pytest`."""

import importlib.util
import json
from pathlib import Path

import pytest
from typesafe_sdk import ChoiceAnswer, TypeSafeAPIConnectionError

_SPEC = importlib.util.spec_from_file_location("ac_judge", Path(__file__).with_name("ac_judge.py"))
ac_judge = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ac_judge)

SPEC_TEXT = """## Acceptance Criteria: Login

### AC-1: Successful login
**Given** a registered user
**When** they log in
**Then** they reach the dashboard

### AC-2: Wrong password
**Given** a registered user
**When** they use a wrong password
**Then** they see "Invalid credentials"

## Out of scope
Single sign-on.
"""

PASSING = {"result": "passed", "tests": ["def test_login(): assert login().path == '/dashboard'"]}


def _answer(choice: str, confidence: float) -> ChoiceAnswer:
    rest = (1 - confidence) / 3
    probabilities = {label: rest for label in ac_judge.JUDGMENT_CRITERIA}
    probabilities[choice] = confidence
    return ChoiceAnswer(
        type="choice", choice=choice, confidence=confidence, probabilities=probabilities
    )


class _Response:
    def __init__(self, choices: dict[str, ChoiceAnswer]):
        self.choices = choices


class FakeClient:
    """Answers system_one from a fixed map of question key → ChoiceAnswer and records calls."""

    def __init__(
        self, answers: dict[str, ChoiceAnswer] | None = None, error: Exception | None = None
    ):
        self.answers = answers or {}
        self.error = error
        self.calls: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def system_one(self, state, questions):
        self.calls.append({"state": state, "questions": questions})
        if self.error:
            raise self.error
        return _Response({key: self.answers[key] for key in questions})


def _criteria():
    return ac_judge.parse_acceptance_criteria(SPEC_TEXT)


def test_parse_reads_heading_criteria_and_stops_at_next_section():
    criteria = _criteria()
    assert [ac.id for ac in criteria] == ["AC-1", "AC-2"]
    assert criteria[0].text.startswith("### AC-1: Successful login")
    assert "dashboard" in criteria[0].text
    assert "Single sign-on" not in criteria[1].text


def test_parse_reads_plain_ac_lines_through_end_of_text():
    criteria = ac_judge.parse_acceptance_criteria("AC-7: Plain\n**Then** it works")
    assert criteria == [ac_judge.AcceptanceCriterion("AC-7", "AC-7: Plain\n**Then** it works")]


def test_parse_returns_nothing_for_spec_without_criteria():
    assert ac_judge.parse_acceptance_criteria("# Notes\nnothing here") == []


@pytest.mark.parametrize(
    ("entry", "verdict"),
    [
        (None, "untested"),
        ({"result": "passed", "tests": []}, "untested"),
        ({"result": "failed", "tests": ["def test_x(): ..."]}, "unmet"),
    ],
)
def test_code_settles_missing_and_failing_evidence(entry, verdict):
    ac = _criteria()[0]
    evidence = {} if entry is None else {"AC-1": entry}
    assert ac_judge.settle_without_model(ac, evidence).verdict == verdict


def test_passing_evidence_is_left_for_the_model():
    assert ac_judge.settle_without_model(_criteria()[0], {"AC-1": PASSING}) is None


@pytest.mark.parametrize(
    ("choice", "confidence", "verdict"),
    [
        ("supports", 0.95, "met"),
        ("supports", 0.6, "needs_review"),
        ("partial", 0.99, "partial"),
        ("contradicts", 0.99, "unmet"),
        ("says_nothing", 0.99, "untested"),
    ],
)
def test_judgment_maps_to_verdict(choice, confidence, verdict):
    result = ac_judge.verdict_from_answer("AC-1", _answer(choice, confidence), threshold=0.8)
    assert result.verdict == verdict
    assert result.judgment == choice
    assert result.confidence == confidence
    assert result.probabilities[choice] == confidence


def test_judge_sends_one_request_for_pending_criteria_only():
    client = FakeClient({"ac_2": _answer("supports", 0.9)})
    evidence = {"AC-2": PASSING}

    verdicts = ac_judge.judge(_criteria(), evidence, client, threshold=0.8)

    assert [(v.ac_id, v.verdict) for v in verdicts] == [("AC-1", "untested"), ("AC-2", "met")]
    assert len(client.calls) == 1
    call = client.calls[0]
    assert set(call["questions"]) == {"ac_2"}
    assert call["state"]["evidence"] == {"ac_2": PASSING["tests"]}
    assert "Wrong password" in call["state"]["criteria"]["ac_2"]
    assert "`criteria.ac_2`" in call["questions"]["ac_2"].instructions
    assert "`evidence.ac_2`" in call["questions"]["ac_2"].instructions


def test_judge_makes_no_request_when_code_settles_everything():
    client = FakeClient()
    verdicts = ac_judge.judge(_criteria(), {}, client, threshold=0.8)
    assert {v.verdict for v in verdicts} == {"untested"}
    assert client.calls == []


def test_report_lists_each_verdict_and_the_tally():
    verdicts = [
        ac_judge.Verdict("AC-1", "met", "fine", "supports", 0.91, {}),
        ac_judge.Verdict("AC-2", "untested", "no tests recorded for this criterion"),
    ]
    assert ac_judge.format_report(verdicts) == (
        "AC-1: met (0.91) — fine\n"
        "AC-2: untested — no tests recorded for this criterion\n"
        "1/2 acceptance criteria met"
    )


@pytest.fixture
def files(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    spec = tmp_path / "spec.md"
    spec.write_text(SPEC_TEXT)
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"AC-1": PASSING, "AC-2": PASSING}))
    return spec, evidence, tmp_path / "verdicts.json"


def _use_client(monkeypatch, client):
    monkeypatch.setattr(ac_judge, "TypeSafeClient", lambda: client)


def test_main_exits_zero_and_writes_verdicts_when_every_ac_is_met(files, monkeypatch, capsys):
    spec, evidence, out = files
    answers = {"ac_1": _answer("supports", 0.9), "ac_2": _answer("supports", 0.95)}
    _use_client(monkeypatch, FakeClient(answers))

    code = ac_judge.main(["--spec", str(spec), "--evidence", str(evidence), "--out", str(out)])

    assert code == 0
    assert "2/2 acceptance criteria met" in capsys.readouterr().out
    assert [v["verdict"] for v in json.loads(out.read_text())] == ["met", "met"]


def test_main_exits_one_when_any_ac_is_not_met(files, monkeypatch, capsys):
    spec, evidence, _ = files
    answers = {"ac_1": _answer("supports", 0.9), "ac_2": _answer("partial", 0.99)}
    _use_client(monkeypatch, FakeClient(answers))

    code = ac_judge.main(["--spec", str(spec), "--evidence", str(evidence)])

    assert code == 1
    assert "AC-2: partial (0.99)" in capsys.readouterr().out


def test_main_skips_without_api_key(files, monkeypatch, capsys):
    spec, evidence, _ = files
    monkeypatch.delenv("TYPESAFE_API_KEY")
    assert ac_judge.main(["--spec", str(spec), "--evidence", str(evidence)]) == 3
    assert capsys.readouterr().out == "skipped: TYPESAFE_API_KEY is not set\n"


def test_main_fails_when_spec_has_no_criteria(files, capsys):
    spec, evidence, _ = files
    spec.write_text("# Notes only\n")
    assert ac_judge.main(["--spec", str(spec), "--evidence", str(evidence)]) == 1
    assert "no AC-N criteria found" in capsys.readouterr().out


def test_main_reports_judge_unavailable_on_api_error(files, monkeypatch, capsys):
    spec, evidence, _ = files
    _use_client(monkeypatch, FakeClient(error=TypeSafeAPIConnectionError("connection refused")))

    code = ac_judge.main(["--spec", str(spec), "--evidence", str(evidence)])

    assert code == 2
    assert "judge unavailable: connection refused" in capsys.readouterr().out
