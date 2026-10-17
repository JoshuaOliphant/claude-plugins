# ABOUTME: Tests claude_config: the one policy for whether a plugin or skill is active on this machine, shared by
# ABOUTME: skill_drift and `pile.py replaced`, against a fake `claude` CLI on PATH and a throwaway ~/.claude.
import json

import claude_config
import pile
import pytest
import skill_drift

HIT = {"kind": "deviated", "p": 0.9, "at": 1, "session": "s1", "turn": "t1", "skill_hash": "v1", "prompt": "p"}


@pytest.mark.parametrize(
    ("listed", "in_settings"),
    [
        ({"id": "old@market", "scope": "user", "enabled": True}, False),
        ({"id": "old@market", "scope": "project", "enabled": False}, True),
        (None, True),
        ({"id": "old@market", "scope": "synced", "enabled": True}, False),
    ],
    ids=["enabled-by-cli-only", "disabled-by-cli", "not-installed", "synced-from-claude-ai"],
)
def test_skill_drift_and_replaced_agree_on_whether_a_plugin_is_active(claude_home, tmp_path, listed, in_settings):
    claude_home.install(*([listed] if listed else []))
    (claude_home.dir / "settings.json").write_text(json.dumps({"enabledPlugins": {"old@market": in_settings}}))
    pile_path = tmp_path / "pile.toml"
    pile_path.write_text('[replaces]\nplugins = ["old@market"]\n')
    log = claude_home.dir / "skill-drift" / "2026-10-01-s.jsonl"
    log.parent.mkdir()
    log.write_text(json.dumps(HIT | {"skill": "old:build", "evidence": "e"}) + "\n")
    replaced_says = "old@market" in pile.replaced(pile_path, claude_home.dir, apply=False)
    drift_says = bool(skill_drift.patterns(claude_home.dir, tmp_path, min_sessions=1)["patterns"])
    assert replaced_says == drift_says == bool(listed and listed["enabled"])


CONFIG = claude_config.Config(
    enabled=frozenset({"compost@oliphant", "old@market"}),
    synced=frozenset({"old@market"}),
    personal=frozenset({"grilling", "tdd"}),
    overrides={"tdd": "off", "compost:pause": "off", "grilling": "user-invocable-only"},
)


@pytest.mark.parametrize(
    ("plugin_id", "enabled", "synced"),
    [("compost@oliphant", True, False), ("old@market", True, True), ("compost@elsewhere", False, False)],
    ids=["plugin-enabled", "synced-plugin-enabled", "same-name-other-marketplace"],
)
def test_a_plugin_is_enabled_and_synced_by_its_full_id(plugin_id, enabled, synced):
    assert (CONFIG.plugin_enabled(plugin_id), CONFIG.is_synced(plugin_id)) == (enabled, synced)


@pytest.mark.parametrize(
    ("name", "active"),
    [
        ("compost:build", True),
        ("compost:pause", False),
        ("plugin-dev:hook-development", False),
        ("grilling", True),
        ("tdd", False),
        ("never-made", False),
    ],
    ids=[
        "skill-of-enabled-plugin",
        "plugin-skill-set-off",
        "skill-of-missing-plugin",
        "personal-skill-hidden-is-not-off",
        "personal-skill-set-off",
        "personal-skill-absent",
    ],
)
def test_skill_active_reads_plugin_skills_and_personal_skills(name, active):
    assert CONFIG.skill_active(name) is active


def test_read_takes_enabled_and_synced_plugins_from_the_cli_and_skills_from_claude_dir(claude_home):
    claude_home.install(
        {"id": "on@m", "scope": "project", "enabled": True},
        {"id": "off@m", "scope": "user", "enabled": False},
        {"id": "web@m", "scope": "synced", "enabled": True},
    )
    assert claude_config.read(claude_home.dir) == claude_config.Config(
        frozenset({"on@m", "web@m"}), frozenset({"web@m"}), frozenset(), {}
    )
    (claude_home.dir / "skills" / "mine").mkdir(parents=True)
    (claude_home.dir / "settings.json").write_text(json.dumps({"skillOverrides": {"x": "off"}}))
    assert claude_config.read(claude_home.dir).personal == frozenset({"mine"})
    assert claude_config.read(claude_home.dir).overrides == {"x": "off"}


@pytest.mark.parametrize(
    ("path", "message"),
    [("", "the claude CLI is not on PATH"), ("failing", "claude plugin list --json failed: boom")],
)
def test_cli_problems_are_reported(claude_home, tmp_path, monkeypatch, path, message):
    if path:
        failing = tmp_path / "failing"
        failing.mkdir()
        (failing / "claude").write_text("#!/bin/sh\necho boom >&2\nexit 1\n")
        (failing / "claude").chmod(0o755)
        path = str(failing)
    monkeypatch.setenv("PATH", path)
    with pytest.raises(claude_config.ClaudeConfigError, match=message):
        claude_config.read(claude_home.dir)


def test_unreadable_settings_are_reported(claude_home):
    (claude_home.dir / "settings.json").write_text("{not json")
    with pytest.raises(claude_config.ClaudeConfigError, match="settings.json is not valid JSON"):
        claude_config.read(claude_home.dir)
