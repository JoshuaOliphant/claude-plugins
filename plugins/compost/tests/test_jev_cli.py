# ABOUTME: Tests jev.py end to end with the network stubbed at the client: tool listing, JSON in and out,
# ABOUTME: and the exit codes skills rely on (2 bad input, 3 Jev unavailable so Claude judges instead).
import io
import json

import jev
import pytest
from conftest import StubClient, choice, noul
from typesafe_sdk import TypeSafeAPIConnectionError


@pytest.fixture
def cache_dir(private_jev_cache):
    return private_jev_cache.parent


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "test_a.py").write_text("def test_one():\n    assert 1\n")
    return tmp_path


def placing(state, questions):
    options = questions["neighbour"].criteria
    return {"neighbour": choice(next(iter(options)), options, 0.95), "covered": noul(0.9)}


def test_list_names_every_tool(capsys):
    assert jev.main(["list"]) == 0
    assert "find-test" in capsys.readouterr().out


def test_a_tool_reads_json_input_and_prints_its_judgment(cache_dir, repo, tmp_path, capsys):
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"repo": str(repo), "criterion": "one is truthy"}))
    assert jev.main(["find-test", "--input", str(source)], client_factory=lambda: StubClient(placing)) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["placements"][0] | {"confidence": None, "covered": None} == {
        "criterion": "one is truthy",
        "action": "extend",
        "test": "test_a.py::test_one",
        "confidence": None,
        "covered": None,
        "alternatives": [],
    }
    assert output["jev"] == {"input_tokens": 100, "cached": 0}
    assert (cache_dir / "jev-cache.json").exists()


def test_input_can_come_from_stdin(cache_dir, repo, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"repo": str(repo), "criterion": "c"})))
    assert jev.main(["find-test"], client_factory=lambda: StubClient(placing)) == 0
    assert json.loads(capsys.readouterr().out)["tool"] == "find-test"


@pytest.mark.parametrize(
    ("text", "message"),
    [("not json", "input is not JSON"), ("[1]", "input must be a JSON object"), ("{}", "needs `criterion`")],
)
def test_bad_input_exits_2(cache_dir, monkeypatch, capsys, text, message):
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    assert jev.main(["find-test"], client_factory=lambda: StubClient(placing)) == jev.EXIT_BAD_INPUT
    assert message in capsys.readouterr().err


def test_unavailable_jev_exits_3_and_says_to_judge_yourself(cache_dir, repo, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"repo": str(repo), "criterion": "c"})))
    failing = StubClient(error=TypeSafeAPIConnectionError("refused"))
    assert jev.main(["find-test"], client_factory=lambda: failing) == jev.EXIT_UNAVAILABLE
    assert "Make this call yourself." in capsys.readouterr().err
