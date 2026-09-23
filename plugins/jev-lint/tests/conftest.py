# ABOUTME: Shared test setup for jev-lint: puts the bundled scripts on sys.path and supplies a stand-in Jev client.
# ABOUTME: The stand-in returns real SDK answer objects so rule interpretation is exercised against the true types.
import sys
from pathlib import Path

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
    """Answers each question id from `answers`, a dict or a function of (state, question id).

    A question id the answers do not cover is left out of the response, as the SDK does for
    answer types it does not recognize. Every request is recorded.
    """

    def __init__(self, answers=None, error=None):
        self.answers = answers or {}
        self.error = error
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def _answer(self, state, question_id):
        if callable(self.answers):
            return self.answers(state, question_id)
        return self.answers.get(question_id)

    async def system_one(self, state, questions):
        self.requests.append({"state": state, "questions": questions})
        if self.error:
            raise self.error
        answers = {question_id: self._answer(state, question_id) for question_id in questions}
        return _Response({key: answer for key, answer in answers.items() if answer is not None})
