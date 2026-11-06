# ABOUTME: Tests jevtools.core: key lookup (env, then Keychain), the content-hash cache, and Jev.ask's
# ABOUTME: caching, token counting, and turning API failures into Unavailable.
import ast
import asyncio
import hashlib
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version

import pytest
from packaging.version import Version
from conftest import PLUGIN_ROOT, StubClient, StubJev, choice, noul, score
from jevtools import core
from jevtools.registry import BadInput
from typesafe_sdk import Choice, Noul, TypeSafeAuthenticationError

QUESTIONS = {"flag": Noul(instructions="Is `text` about tests?")}
SDK = Version(version("typesafe-sdk"))
SCRIPTS = PLUGIN_ROOT / "scripts"


def fake_security(tmp_path, monkeypatch, script: str) -> None:
    binary = tmp_path / "bin" / "security"
    binary.parent.mkdir()
    binary.write_text(f"#!/bin/sh\n{script}\n")
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(binary.parent))


def test_environment_key_wins(monkeypatch):
    monkeypatch.setenv(core.ENV_VAR, "from-env")
    assert core.resolve_key() == "from-env"


@pytest.mark.parametrize(("script", "expected"), [("echo from-keychain", "from-keychain"), ("exit 44", None)])
def test_keychain_is_the_fallback(tmp_path, monkeypatch, script, expected):
    monkeypatch.delenv(core.ENV_VAR, raising=False)
    fake_security(tmp_path, monkeypatch, script)
    assert core.resolve_key() == expected


def test_open_client_without_a_key_explains_how_to_store_one(monkeypatch):
    monkeypatch.delenv(core.ENV_VAR, raising=False)
    monkeypatch.setenv("PATH", "")
    with pytest.raises(core.Unavailable, match="security add-generic-password -s typesafe"):
        core.open_client()


@pytest.mark.parametrize(
    ("key", "proxy", "reason"),
    [
        pytest.param(
            "two words",
            None,
            "API key must contain only printable ASCII",
            id="malformed-key",
            marks=pytest.mark.skipif(
                SDK < Version("0.7.1"), reason="typesafe-sdk validates keys from 0.7.1, jev.py's floor"
            ),
        ),
        pytest.param("k", "ftp://127.0.0.1:1", "Unknown scheme for proxy URL", id="unknown-proxy-scheme"),
        pytest.param(
            "k",
            "socks5://127.0.0.1:1",
            "socksio",
            id="socks-proxy-without-socksio",
            marks=pytest.mark.skipif(importlib.util.find_spec("socksio") is not None, reason="socksio is installed"),
        ),
    ],
)
def test_a_client_that_cannot_start_is_unavailable(monkeypatch, key, proxy, reason):
    monkeypatch.setenv(core.ENV_VAR, key)
    for name in ("HTTPS_PROXY", "https_proxy"):
        if proxy:
            monkeypatch.setenv(name, proxy)
        else:
            monkeypatch.delenv(name, raising=False)
    with pytest.raises(core.Unavailable, match=f"TypeSafe client could not start: .*{reason}"):
        core.open_client()


def test_typesafe_and_jev_latest_are_the_defaults():
    assert (core.base_url(), core.model()) == ("https://api.typesafe.ai", "jev-latest")


def test_the_sdk_variables_pick_another_server_and_model(monkeypatch):
    monkeypatch.setenv(core.BASE_URL_VAR, "http://localhost:11435/")
    monkeypatch.setenv(core.MODEL_VAR, "winnow:e4b")
    assert (core.base_url(), core.model()) == ("http://localhost:11435", "winnow:e4b")


def test_another_server_never_gets_the_keychain_key(tmp_path, monkeypatch):
    monkeypatch.delenv(core.ENV_VAR, raising=False)
    monkeypatch.setenv(core.BASE_URL_VAR, "http://localhost:11435")
    fake_security(tmp_path, monkeypatch, "echo typesafe-secret")
    assert core.resolve_key() == core.LOCAL_KEY


def test_another_server_gets_an_exported_key(monkeypatch):
    monkeypatch.setenv(core.ENV_VAR, "ollaya-key")
    monkeypatch.setenv(core.BASE_URL_VAR, "http://localhost:11435")
    assert core.resolve_key() == "ollaya-key"


@pytest.mark.parametrize(
    ("url", "carries"),
    [
        ("https://decisions.example.com", True),
        ("http://localhost:11435", True),
        ("http://127.0.0.2:11435", True),
        ("http://[::1]:11435", True),
        ("http://192.168.1.20:11435", False),
        ("http://ollaya.lan:11435", False),
    ],
)
def test_an_exported_key_goes_only_over_https_or_to_this_machine(monkeypatch, url, carries):
    monkeypatch.setenv(core.ENV_VAR, "exported")
    monkeypatch.setenv(core.BASE_URL_VAR, url)
    assert core.resolve_key() == ("exported" if carries else core.LOCAL_KEY)


class OllayaStandIn(BaseHTTPRequestHandler):
    """Speaks the slice of Ollaya's /v1/systemone that one Noul needs, and records what reached it."""

    seen: list[dict] = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).seen.append({"path": self.path, "auth": self.headers["Authorization"], "model": body["model"]})
        answers = {name: {"type": "noul", "noul": 0.3} for name in body["questions"]}
        out = json.dumps({"model": body["model"], "answers": answers, "usage": {"input_tokens": 7, "output_tokens": 0}})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out.encode())

    def log_message(self, *args):
        pass


def test_open_client_reaches_the_configured_server_with_its_model_and_the_placeholder(tmp_path, monkeypatch):
    OllayaStandIn.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), OllayaStandIn)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.delenv(core.ENV_VAR, raising=False)
    monkeypatch.setenv(core.BASE_URL_VAR, f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv(core.MODEL_VAR, "winnow:e4b")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")

    async def ask():
        async with core.session(cache=core.Cache(tmp_path / "c.json")) as jev:
            return await jev.ask("t", {"text": "a"}, QUESTIONS)

    try:
        assert asyncio.run(ask()).noul("flag") == 0.3
    finally:
        server.shutdown()
    assert OllayaStandIn.seen == [{"path": "/v1/systemone", "auth": "Bearer local", "model": "winnow:e4b"}]


def test_ask_names_the_configured_model(tmp_path, monkeypatch):
    monkeypatch.setenv(core.MODEL_VAR, "winnow:e4b")
    client = StubClient(lambda state, asked: {"flag": noul(0.7)})
    asyncio.run(core.Jev(client, core.Cache(tmp_path / "c.json")).ask("t", {"text": "a"}, QUESTIONS))
    assert client.models == ["winnow:e4b"]


def test_open_client_with_a_key(monkeypatch):
    monkeypatch.setenv(core.ENV_VAR, "k")
    assert core.open_client() is not None


def test_cache_round_trips_through_its_file(tmp_path):
    path = tmp_path / "nested" / "cache.json"
    cache = core.Cache(path)
    cache.put("k", {"flag": noul(0.2)})
    cache.save()
    assert core.Cache(path).get("k") == {"flag": noul(0.2)}
    assert core.Cache(path).get("absent") is None


def test_an_unreadable_cache_starts_empty_and_is_replaced_whole(tmp_path):
    path = tmp_path / "cache.json"
    path.write_text('{"k": {"flag": ')
    cache = core.Cache(path)
    assert cache.get("k") is None
    cache.put("k", {"flag": noul(0.4)})
    cache.save()
    assert core.Cache(path).get("k") == {"flag": noul(0.4)}
    assert [p.name for p in tmp_path.iterdir()] == ["cache.json"]


def test_cache_key_depends_on_tool_state_and_question_text():
    base = core.cache_key("t", {"text": "a"}, QUESTIONS)
    assert base == core.cache_key("t", {"text": "a"}, QUESTIONS)
    assert base != core.cache_key("u", {"text": "a"}, QUESTIONS)
    assert base != core.cache_key("t", {"text": "b"}, QUESTIONS)
    assert base != core.cache_key("t", {"text": "a"}, {"flag": Noul(instructions="Is `text` about code?")})


def test_cache_keys_on_typesafe_are_the_ones_written_before_other_servers_were_possible():
    described = {name: question.model_dump(mode="json") for name, question in QUESTIONS.items()}
    before = json.dumps(["jev-latest", "t", {"text": "a"}, described], sort_keys=True, default=str)
    assert core.cache_key("t", {"text": "a"}, QUESTIONS) == hashlib.sha256(before.encode()).hexdigest()


@pytest.mark.parametrize(
    ("variable", "value"), [("MODEL_VAR", "winnow:e4b"), ("BASE_URL_VAR", "http://localhost:11435")]
)
def test_cache_key_depends_on_the_model_and_server(monkeypatch, variable, value):
    base = core.cache_key("t", {"text": "a"}, QUESTIONS)
    monkeypatch.setenv(getattr(core, variable), value)
    assert base != core.cache_key("t", {"text": "a"}, QUESTIONS)


def test_api_failures_become_unavailable(tmp_path):
    jev = core.Jev(StubClient(error=OSError("ssl")), core.Cache(tmp_path / "c.json"))
    with pytest.raises(core.Unavailable, match="Jev request failed"):
        asyncio.run(jev.ask("t", {"text": "a"}, QUESTIONS))


@pytest.mark.parametrize(
    ("url", "explained"),
    [("http://192.168.1.20:11435", True), ("https://decisions.example.com", False), ("http://localhost:11435", False)],
)
def test_a_refused_placeholder_says_how_to_send_a_key(tmp_path, monkeypatch, url, explained):
    monkeypatch.setenv(core.BASE_URL_VAR, url)
    refused = TypeSafeAuthenticationError(401, {"error": "unauthorized"}, {})
    jev = core.Jev(StubClient(error=refused), core.Cache(tmp_path / "c.json"))
    with pytest.raises(core.Unavailable) as raised:
        asyncio.run(jev.ask("t", {"text": "a"}, QUESTIONS))
    assert ("tunnel it to localhost" in str(raised.value)) is explained


def test_a_dropped_answer_is_unavailable_and_nothing_is_cached(tmp_path):
    questions = {**QUESTIONS, "other": Noul(instructions="Is `text` long?")}
    jev = core.Jev(StubClient(lambda state, asked: {"flag": noul(0.7)}), core.Cache(tmp_path / "c.json"))
    with pytest.raises(core.Unavailable, match="Jev returned no answer for other"):
        asyncio.run(jev.ask("t", {"text": "a"}, questions))
    assert jev.cache.entries == {}


def test_a_partial_answer_cached_before_is_asked_again(tmp_path):
    questions = {**QUESTIONS, "other": Noul(instructions="Is `text` long?")}
    cache = core.Cache(tmp_path / "c.json")
    cache.put(core.cache_key("t", {"text": "a"}, questions), {"flag": noul(0.7)})
    client = StubClient(lambda state, asked: {"flag": noul(0.7), "other": noul(0.1)})
    answers = asyncio.run(core.Jev(client, cache).ask("t", {"text": "a"}, questions))
    assert (answers.noul("flag"), answers.noul("other")) == (0.7, 0.1)
    assert len(client.calls) == 1


def test_answers_are_read_through_the_view_and_cached_as_plain_dicts(tmp_path):
    raw = {"flag": noul(0.7), "pick": choice("b", probabilities={"a": 0.2, "b": 0.5, "c": 0.3}), "grade": score(2.4)}
    path = tmp_path / "c.json"
    client = StubClient(lambda state, asked: raw)
    jev = core.Jev(client, core.Cache(path))
    fresh = asyncio.run(jev.ask("t", {"text": "a"}, QUESTIONS))
    jev.cache.save()
    cached = asyncio.run(core.Jev(client, core.Cache(path)).ask("t", {"text": "a"}, QUESTIONS))
    for answers in (fresh, cached):
        assert answers.noul("flag") == 0.7
        assert answers.ranked("pick") == [("b", 0.5), ("c", 0.3), ("a", 0.2)]
        assert answers.ranked("pick", 1) == [("b", 0.5)]
        assert list(answers.probabilities("pick").items()) == [("a", 0.2), ("b", 0.5), ("c", 0.3)]
        assert (answers.score("grade"), answers.confidence("grade")) == (2.4, 0.8)
    assert core.Cache(path).get(core.cache_key("t", {"text": "a"}, QUESTIONS)) == raw
    assert len(client.calls) == 1


def answer_reads(source: str) -> list[int]:
    """Lines that reach past the Answers view: a subscript on a `jev.ask` result (directly or through the name it
    was bound to), or a read of the view's `.raw` dicts. The view has no `__getitem__`, so any other subscript on
    it fails at run time."""
    tree = ast.parse(source)

    def is_ask(node) -> bool:
        call = node.value if isinstance(node, ast.Await) else None
        return isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "ask"

    bound = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and is_ask(node.value)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Subscript)
            and (is_ask(node.value) or (isinstance(node.value, ast.Name) and node.value.id in bound))
        )
        or (isinstance(node, ast.Attribute) and node.attr == "raw")
    )


def test_answer_reads_finds_every_way_of_indexing_an_answer():
    source = (
        'async def f(jev, answer):\n    a = await jev.ask("t", {}, {})\n    a["q"]\n'
        '    (await jev.ask("t", {}, {}))["q"]\n    answers.raw["q"]["noul"]\n    entry["score"]\n'
    )
    assert answer_reads(source) == [3, 4, 5]


TOOLS = [*sorted((SCRIPTS / "jevtools").glob("*.py")), SCRIPTS / "jev.py", *sorted((SCRIPTS / "lint").glob("*.py"))]


@pytest.mark.parametrize("module", TOOLS, ids=lambda path: str(path.relative_to(SCRIPTS)))
def test_tools_read_answers_only_through_the_view_and_core_owns_the_cap(module):
    source = module.read_text()
    assert answer_reads(source) == [] or module.name == "core.py"
    owners = [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Assign) and any(getattr(target, "id", "") == "CHOICE_LIMIT" for target in node.targets)
    ]
    assert len(owners) == (module.name == "core.py")


def picking_group(label: str, *, exists: float | None = None):
    def answer(tool, state, questions):
        answers = {"group": choice(label, questions["group"].criteria)}
        return answers | ({"exists": noul(exists)} if exists is not None else {})

    return answer


def group_question(groups: dict[str, list[str]]) -> Choice:
    return Choice(
        instructions="Which group?", criteria={label: ", ".join(members) for label, members in groups.items()}
    )


def test_narrow_asks_nothing_when_every_option_fits(monkeypatch):
    monkeypatch.setattr(core, "CHOICE_LIMIT", 3)
    jev = StubJev(picking_group("a"))
    options, answers = asyncio.run(core.narrow(jev, "t", {}, {"a": ["1", "2"], "b": ["3"]}, group_question))
    assert (options, answers, jev.calls) == (["1", "2", "3"], None, [])


@pytest.mark.parametrize(
    ("groups", "chosen", "keep", "kept"),
    [
        ({"a": ["1"], "b": ["2"], "c": ["3", "4"]}, "a", None, ["1"]),
        ({"a": ["1"], "b": ["2"], "c": ["3", "4"]}, "a", 2, ["1", "2"]),
        ({"a": ["1", "2"], "b": ["3"], "c": ["4"]}, "a", 2, ["1", "2", "3"]),
        ({"a": ["1", "2", "3"], "b": ["4"]}, "a", 2, ["1", "2", "3"]),
        ({"a": ["1", "2"], "b": ["3", "4"], "c": ["5"]}, "a", 3, ["1", "2", "5"]),
    ],
    ids=[
        "keeps one group by default",
        "keeps the likeliest groups up to keep",
        "fills the cap exactly",
        "stops before the cap",
        "skips a group past the cap for a smaller likely one",
    ],
)
def test_narrow_keeps_the_likeliest_groups_within_the_cap(monkeypatch, groups, chosen, keep, kept):
    monkeypatch.setattr(core, "CHOICE_LIMIT", 3)
    jev = StubJev(picking_group(chosen, exists=0.6))
    keeping = {} if keep is None else {"keep": keep}
    options, answers = asyncio.run(
        core.narrow(jev, "t", {"s": 1}, groups, group_question, **keeping, also={"exists": Noul(instructions="?")})
    )
    assert options == kept
    assert answers.noul("exists") == 0.6
    tool, state, questions = jev.calls[0]
    assert (tool, state, set(questions)) == ("t", {"s": 1}, {"group", "exists"})


def test_narrow_splits_a_group_past_the_cap_so_every_option_stays_reachable(monkeypatch):
    monkeypatch.setattr(core, "CHOICE_LIMIT", 3)
    groups = {"big": ["1", "2", "3", "4", "5"], "small": ["6"]}
    jev = StubJev(picking_group("big (part 2 of 2)"))
    options, _ = asyncio.run(core.narrow(jev, "t", {}, groups, group_question))
    asked = jev.calls[0][2]["group"].criteria
    assert asked == {"big (part 1 of 2)": "1, 2, 3", "big (part 2 of 2)": "4, 5", "small": "6"}
    assert options == ["4", "5"]


def test_narrow_reports_options_two_stages_cannot_reach(monkeypatch):
    monkeypatch.setattr(core, "CHOICE_LIMIT", 2)
    jev = StubJev(picking_group("a"))
    with pytest.raises(BadInput, match="5 options in 3 groups; at most 2 groups"):
        asyncio.run(core.narrow(jev, "t", {}, {"a": ["1", "2"], "b": ["3", "4"], "c": ["5"]}, group_question))
    assert jev.calls == []
