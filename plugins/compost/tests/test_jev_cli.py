# ABOUTME: Tests jev.py end to end with the network stubbed at the client: tool listing, JSON in and out,
# ABOUTME: and the exit codes skills rely on (2 bad input, 3 Jev unavailable so Claude judges instead).
import io
import json

import httpx2
import jev
import pytest
from conftest import StubClient, choice, noul
from jevtools import core
from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy, TypeSafeAPIConnectionError


@pytest.fixture
def cache_dir(private_jev_cache):
    return private_jev_cache.parent


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "test_a.py").write_text("def test_one():\n    assert 1\n")
    return tmp_path


def placing(state, questions):
    if "covered" in questions:
        return {"covered": noul(0.9)}
    options = questions["neighbour"].criteria
    return {"neighbour": choice(next(iter(options)), options, 0.95)}


def test_status_reports_a_key_without_calling_the_api(monkeypatch, capsys):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    assert jev.main(["status"]) == 0
    assert capsys.readouterr().out.startswith("jev ready: a TypeSafe key was found; 17 tools available")


def test_status_without_a_key_exits_3_and_says_how_to_store_one(monkeypatch, capsys):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("PATH", "")
    assert jev.main(["status"]) == jev.EXIT_UNAVAILABLE
    assert "security add-generic-password -s typesafe" in capsys.readouterr().err


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
    assert output["jev"] == {"input_tokens": 200, "cached": 0}
    assert (cache_dir / "jev-cache.json").exists()


@pytest.mark.parametrize(
    ("text", "message"),
    [("not json", "input is not JSON"), ("[1]", "input must be a JSON object"), ("{}", "needs `criterion`")],
)
def test_bad_input_exits_2(cache_dir, monkeypatch, capsys, text, message):
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    assert jev.main(["find-test"], client_factory=lambda: StubClient(placing)) == jev.EXIT_BAD_INPUT
    assert message in capsys.readouterr().err


def through(handler):
    """A real TypeSafe client whose HTTP transport is `handler`, so the SDK's own error wrapping runs."""
    transport = httpx2.MockTransport(handler)
    return lambda: AsyncTypeSafeClient(api_key="k", transport=transport, retry=RetryPolicy(max_retries=0))


def refuse(error):
    def handler(request):
        raise error

    return handler


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(through(refuse(httpx2.ConnectError("All connection attempts failed"))), id="connection-refused"),
        pytest.param(through(refuse(httpx2.ProxyError("403 Forbidden"))), id="proxy-tunnel-403"),
        pytest.param(
            through(lambda request: httpx2.Response(403, text="<html>\n<body>blocked by policy</body>\n</html>\n")),
            id="proxy-403-page",
        ),
        pytest.param(core.open_client, id="proxy-setting-unusable"),
        pytest.param(
            lambda: StubClient(error=TypeSafeAPIConnectionError("Server disconnected without sending a response.")),
            id="api-refused",
        ),
        pytest.param(lambda: StubClient(lambda state, questions: {}), id="answer-dropped"),
    ],
)
def test_unavailable_jev_exits_3_with_one_line_saying_to_judge_yourself(cache_dir, repo, monkeypatch, capsys, factory):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    for name in ("HTTPS_PROXY", "https_proxy"):
        monkeypatch.setenv(name, "ftp://127.0.0.1:1")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"repo": str(repo), "criterion": "c"})))
    assert jev.main(["find-test"], client_factory=factory) == jev.EXIT_UNAVAILABLE
    [line] = capsys.readouterr().err.splitlines()
    assert line.startswith("jev unavailable: ")
    assert line.endswith("Make this call yourself.")
    assert ".." not in line
