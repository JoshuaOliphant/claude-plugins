# ABOUTME: Tests the compost:implement Stop hook: when it acts (an implement run, not already continuing), how it finds
# ABOUTME: the final message, and that every failure allows the stop and leaves one line in the log.
import io
import json

import pytest
import stop_guard
from conftest import StubClient, noul
from jevtools.core import Unavailable

LOADS_IMPLEMENT = {
    "type": "assistant",
    "message": {
        "id": "m0",
        "content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "compost:implement"}}],
    },
}
SLASH_IMPLEMENT = {
    "type": "user",
    "message": {
        "content": "<command-message>compost:implement</command-message>\n<command-name>/compost:implement</command-name>"
    },
}
SKILL_LISTING = {
    "type": "attachment",
    "attachment": {"content": "- compost:implement: the entry point once issues exist"},
}


def said(message_id: str, text: str, **extra) -> dict:
    return {"type": "assistant", "message": {"id": message_id, "content": [{"type": "text", "text": text}]}, **extra}


@pytest.fixture
def log(tmp_path, monkeypatch):
    path = tmp_path / "logs" / "stop-guard.log"
    monkeypatch.setattr(stop_guard, "LOG", path)
    return path


@pytest.fixture
def transcript(tmp_path):
    def write(*entries, raw: str = "") -> str:
        path = tmp_path / "session.jsonl"
        path.write_text(raw + "".join(json.dumps(entry) + "\n" for entry in entries))
        return str(path)

    return write


def judging(waits: float, allowed: float):
    return lambda: StubClient(lambda state, questions: {"waits": noul(waits), "allowed": noul(allowed)})


def test_a_question_mid_implement_is_sent_back_with_the_ruling_instruction(transcript):
    path = transcript(LOADS_IMPLEMENT, said("m1", "Which library do you prefer?"))
    verdict = stop_guard.decide({"transcript_path": path, "stop_hook_active": False}, judging(0.9, 0.1))
    assert verdict == {"decision": "block", "reason": stop_guard.REASON}
    assert "post a ruling as an issue comment" in verdict["reason"]


def test_an_allowed_stop_goes_through(transcript):
    path = transcript(SLASH_IMPLEMENT, said("m1", "All issues landed. Shall I merge to main?"))
    assert stop_guard.decide({"transcript_path": path}, judging(0.9, 0.9)) is None


def test_a_stop_hook_continuation_is_never_blocked_again(tmp_path):
    hook = {"transcript_path": str(tmp_path / "never-read.jsonl"), "stop_hook_active": True}
    assert stop_guard.decide(hook, judging(1.0, 0.0)) is None


@pytest.mark.parametrize(
    "entries",
    [[said("m1", "Which library do you prefer?")], [SKILL_LISTING, said("m1", "Which library do you prefer?")]],
    ids=["implement never mentioned", "implement only listed, never loaded"],
)
def test_sessions_that_never_loaded_implement_are_left_alone(transcript, entries):
    client = StubClient(lambda state, questions: {})
    assert stop_guard.decide({"transcript_path": transcript(*entries)}, lambda: client) is None
    assert client.calls == []


def test_the_final_message_comes_from_the_hook_input_when_given(transcript):
    client = StubClient(lambda state, questions: {"waits": noul(0.1), "allowed": noul(0.1)})
    path = transcript(LOADS_IMPLEMENT, said("m1", "from the transcript"))
    stop_guard.decide({"transcript_path": path, "last_assistant_message": "from the hook"}, lambda: client)
    assert client.calls[0][0]["message"] == "from the hook"


def test_the_final_message_is_the_last_main_thread_reply_read_from_the_transcript(transcript):
    client = StubClient(lambda state, questions: {"waits": noul(0.1), "allowed": noul(0.1)})
    path = transcript(
        LOADS_IMPLEMENT,
        said("m1", "An earlier reply."),
        {"type": "summary", "message": "not a dict of content"},
        said("m2", "Two options: dateparser or pendulum."),
        {"type": "assistant", "message": {"id": "m2", "content": [{"type": "tool_use", "name": "Bash"}, "stray"]}},
        said("m2", "Which library do you prefer?"),
        said("s1", "A subagent's reply.", isSidechain=True),
        raw="not json\n[1, 2]\n",
    )
    stop_guard.decide({"transcript_path": path}, lambda: client)
    assert client.calls[0][0]["message"] == "Two options: dateparser or pendulum.\nWhich library do you prefer?"


def test_a_turn_with_no_text_is_not_judged(transcript):
    client = StubClient(lambda state, questions: {})
    assert stop_guard.decide({"transcript_path": transcript(LOADS_IMPLEMENT)}, lambda: client) is None
    assert client.calls == []


def test_main_prints_the_block_for_claude_code(transcript, capsys, log):
    path = transcript(LOADS_IMPLEMENT, said("m1", "Which library do you prefer?"))
    assert stop_guard.main(io.StringIO(json.dumps({"transcript_path": path})), judging(0.9, 0.1)) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "block"
    assert not log.exists()


def test_main_reads_stdin_and_prints_nothing_when_the_stop_is_allowed(transcript, capsys, monkeypatch):
    path = transcript(LOADS_IMPLEMENT, said("m1", "Done: PR #52 is up and the suite is green."))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"transcript_path": path})))
    assert stop_guard.main(client_factory=judging(0.05, 0.3)) == 0
    assert capsys.readouterr().out == ""


def refuse():
    raise Unavailable("TYPESAFE_API_KEY is not set")


@pytest.mark.parametrize(
    ("stdin", "client_factory", "logged"),
    [
        ("not json", judging(1.0, 0.0), "allowed the stop after JSONDecodeError"),
        (json.dumps({}), judging(1.0, 0.0), "allowed the stop after KeyError"),
        (None, refuse, "allowed the stop after Unavailable: TYPESAFE_API_KEY is not set"),
    ],
    ids=["bad hook json", "no transcript path", "no key"],
)
def test_any_failure_allows_the_stop_silently_and_logs_one_line(transcript, capsys, log, stdin, client_factory, logged):
    hook = stdin or json.dumps({"transcript_path": transcript(LOADS_IMPLEMENT, said("m1", "Which one?"))})
    assert stop_guard.main(io.StringIO(hook), client_factory) == 0
    assert capsys.readouterr().out == ""
    [line] = log.read_text().splitlines()
    assert logged in line
