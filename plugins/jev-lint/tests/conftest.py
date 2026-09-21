# ABOUTME: Shared test setup for jev-lint: puts the bundled scripts on sys.path and supplies a stand-in Jev client.
# ABOUTME: The stand-in returns real SDK answer objects so rule interpretation is exercised against the true types.
import sys
from pathlib import Path

import pytest
from typesafe_sdk import ChoiceAnswer, NoulAnswer

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def noul(probability: float) -> NoulAnswer:
    return NoulAnswer(type="noul", noul=probability)


def choice(probabilities: dict[str, float]) -> ChoiceAnswer:
    top = max(probabilities, key=probabilities.get)
    return ChoiceAnswer(
        type="choice", choice=top, confidence=probabilities[top], probabilities=probabilities
    )


class _Response:
    def __init__(self, answers):
        self.answers = answers


class FakeJev:
    """Answers each question id from `answers`; records every request it receives."""

    def __init__(self, answers=None, error=None):
        self.answers = answers or {}
        self.error = error
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def system_one(self, state, questions):
        self.requests.append({"state": state, "questions": questions})
        if self.error:
            raise self.error
        return _Response({question_id: self.answers[question_id] for question_id in questions})


@pytest.fixture
def fake_jev():
    return FakeJev
