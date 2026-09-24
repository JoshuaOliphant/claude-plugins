# ABOUTME: Tests jevtools.core: key lookup (env, then Keychain), the content-hash cache, and Jev.ask's
# ABOUTME: caching, token counting, and turning API failures into Unavailable.
import asyncio

import pytest
from conftest import StubClient, noul
from jevtools import core
from typesafe_sdk import Noul, TypeSafeAPIConnectionError

QUESTIONS = {"flag": Noul(instructions="Is `text` about tests?")}


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


def test_no_security_binary_means_no_key(monkeypatch):
    monkeypatch.delenv(core.ENV_VAR, raising=False)
    monkeypatch.setenv("PATH", "")
    assert core.resolve_key() is None


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


def test_ask_counts_tokens_then_serves_repeats_from_the_cache(tmp_path):
    client = StubClient(lambda state, questions: {"flag": noul(0.7)})
    jev = core.Jev(client, core.Cache(tmp_path / "c.json"))
    first = asyncio.run(jev.ask("t", {"text": "a"}, QUESTIONS))
    second = asyncio.run(jev.ask("t", {"text": "a"}, QUESTIONS))
    assert first == second == {"flag": {"type": "noul", "noul": 0.7}}
    assert (len(client.calls), jev.input_tokens, jev.cached) == (1, 100, 1)


@pytest.mark.parametrize("error", [TypeSafeAPIConnectionError("refused"), OSError("ssl")])
def test_api_failures_become_unavailable(tmp_path, error):
    jev = core.Jev(StubClient(error=error), core.Cache(tmp_path / "c.json"))
    with pytest.raises(core.Unavailable, match="Jev request failed"):
        asyncio.run(jev.ask("t", {"text": "a"}, QUESTIONS))


def test_top_orders_by_probability():
    assert core.top({"a": 0.2, "b": 0.5, "c": 0.3}, 2) == [("b", 0.5), ("c", 0.3)]
