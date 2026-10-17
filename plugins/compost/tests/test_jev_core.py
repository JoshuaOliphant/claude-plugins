# ABOUTME: Tests jevtools.core: key lookup (env, then Keychain), the content-hash cache, and Jev.ask's
# ABOUTME: caching, token counting, and turning API failures into Unavailable.
import ast
import asyncio

import pytest
from conftest import PLUGIN_ROOT, StubClient, StubJev, choice, noul, score
from jevtools import core
from jevtools.registry import BadInput
from typesafe_sdk import Choice, Noul

QUESTIONS = {"flag": Noul(instructions="Is `text` about tests?")}
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


def test_api_failures_become_unavailable(tmp_path):
    jev = core.Jev(StubClient(error=OSError("ssl")), core.Cache(tmp_path / "c.json"))
    with pytest.raises(core.Unavailable, match="Jev request failed"):
        asyncio.run(jev.ask("t", {"text": "a"}, QUESTIONS))


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
    """Lines where the result of `jev.ask` is subscripted, directly or through the name it was bound to."""
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
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and (is_ask(node.value) or (isinstance(node.value, ast.Name) and node.value.id in bound))
    ]


def test_answer_reads_finds_both_ways_of_indexing_an_answer():
    source = (
        'async def f(jev):\n    a = await jev.ask("t", {}, {})\n    a["q"]\n    (await jev.ask("t", {}, {}))["q"]\n'
    )
    assert answer_reads(source) == [3, 4]


@pytest.mark.parametrize(
    "module", [*sorted((SCRIPTS / "jevtools").glob("*.py")), SCRIPTS / "jev.py"], ids=lambda path: path.name
)
def test_tools_read_answers_only_through_the_view_and_core_owns_the_cap(module):
    source = module.read_text()
    assert answer_reads(source) == []
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
    ],
    ids=[
        "keeps one group by default",
        "keeps the likeliest groups up to keep",
        "fills the cap exactly",
        "stops before the cap",
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
