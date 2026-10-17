# ABOUTME: Tests claude_config: the one policy for whether a plugin or skill is active on this machine, shared by
# ABOUTME: skill_drift and `pile.py replaced`, against a fake `claude` CLI on PATH and a throwaway ~/.claude.
import json
import re

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
    personal=frozenset({"grilling", "tdd"}),
    overrides={"tdd": "off", "compost:pause": "off", "grilling": "user-invocable-only"},
    list_plugins=lambda: [
        {"id": "compost@oliphant", "scope": "user", "enabled": True},
        {"id": "old@market", "scope": "synced", "enabled": True},
        {"id": "both@market", "scope": "synced", "enabled": True},
        {"id": "both@market", "scope": "project", "enabled": True},
    ],
)


@pytest.mark.parametrize(
    ("plugin_id", "enabled", "synced"),
    [
        ("compost@oliphant", True, False),
        ("old@market", True, True),
        ("both@market", True, False),
        ("compost@elsewhere", False, False),
    ],
    ids=[
        "plugin-enabled",
        "synced-plugin-enabled",
        "synced-and-local-is-turned-off-locally",
        "same-name-other-marketplace",
    ],
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
    config = claude_config.read(claude_home.dir)
    assert (config.enabled, config.synced, config.personal, config.overrides) == (
        frozenset({"on@m", "web@m"}),
        frozenset({"web@m"}),
        frozenset(),
        {},
    )
    (claude_home.dir / "skills" / "mine").mkdir(parents=True)
    (claude_home.dir / "settings.json").write_text(json.dumps({"skillOverrides": {"x": "off"}}))
    assert claude_config.read(claude_home.dir).personal == frozenset({"mine"})
    assert claude_config.read(claude_home.dir).overrides == {"x": "off"}


@pytest.mark.parametrize("default", [False, True], ids=["other-claude-dir", "default-claude-dir"])
def test_the_cli_lists_plugins_from_the_claude_dir_the_settings_come_from(claude_home, monkeypatch, default):
    if default:
        monkeypatch.setattr(claude_config, "CLAUDE_DIR", claude_home.dir)
    assert claude_config.read(claude_home.dir).enabled == frozenset()
    assert claude_home.calls.read_text() == f"list {'unset' if default else claude_home.dir}\n"


def test_plugins_are_listed_only_when_a_plugin_is_asked_about(claude_home):
    (claude_home.dir / "skills" / "mine").mkdir(parents=True)
    config = claude_config.read(claude_home.dir)
    assert (config.skill_active("mine"), config.skill_active("gone")) == (True, False)
    assert not claude_home.calls.exists()
    assert not config.skill_active("compost:build")
    assert not config.plugin_enabled("compost@oliphant")
    assert claude_home.calls.read_text() == f"list {claude_home.dir}\n"


@pytest.mark.parametrize(
    ("listing", "asked", "command"),
    [("listing", "enabled", "plugin list"), ("marketplaces", "orphaned", "plugin marketplace list")],
    ids=["plugin-list", "marketplace-list"],
)
def test_unparseable_cli_output_is_reported(claude_home, listing, asked, command):
    getattr(claude_home, listing).write_text("Warning: update available\n[]")
    with pytest.raises(claude_config.ClaudeConfigError, match=f"claude {command} --json printed no JSON: "):
        getattr(claude_config.read(claude_home.dir), asked)


def test_orphans_come_only_from_marketplaces_whose_clone_has_a_catalog(claude_home):
    claude_home.install(
        {"id": "kept@listed", "scope": "user", "enabled": True},
        {"id": "dropped@listed", "scope": "local", "enabled": False},
        {"id": "dropped@uncloned", "scope": "user", "enabled": True},
        {"id": "dropped@managed", "scope": "managed", "enabled": True},
        {"id": "dropped@pending", "scope": "user", "enabled": True},
    )
    (claude_home.add_marketplace("uncloned") / ".claude-plugin" / "marketplace.json").unlink()
    nameless = claude_home.add_marketplace("nameless")
    configured = json.loads(claude_home.marketplaces.read_text())
    configured[-1] = {"source": "github", "repo": "acme/nameless", "installLocation": str(nameless)}
    configured.append({"name": "pending", "source": "github", "repo": "acme/pending"})
    claude_home.marketplaces.write_text(json.dumps(configured))
    claude_home.add_marketplace("listed", "kept")
    claude_home.add_marketplace("managed")
    assert claude_config.read(claude_home.dir).orphaned == [("dropped@listed", "local")]


@pytest.mark.parametrize(
    ("catalog", "message"),
    [
        (b"{not json", ": Expecting property name.*"),
        (b"\xff", ": 'utf-8' codec.*"),
        (b"[]", " does not list plugins by name"),
        (b"{}", " does not list plugins by name"),
        (b'{"plugins": {"a": {}}}', " does not list plugins by name"),
        (b'{"plugins": [{"source": "./a"}]}', " does not list plugins by name"),
        (b'{"plugins": ["a"]}', " does not list plugins by name"),
    ],
    ids=[
        "not-json",
        "not-utf8",
        "top-level-list",
        "no-plugins",
        "plugins-not-list",
        "entry-without-name",
        "entry-not-object",
    ],
)
def test_a_malformed_marketplace_catalog_is_skipped_with_a_warning(claude_home, tmp_path, capsys, catalog, message):
    claude_home.install({"id": "gone@broken", "scope": "user", "enabled": True})
    (claude_home.dir / "skills" / "tdd").mkdir(parents=True)
    clone = claude_home.add_marketplace("broken")
    (clone / ".claude-plugin" / "marketplace.json").write_bytes(catalog)
    pile_path = tmp_path / "pile.toml"
    pile_path.write_text('[replaces]\nskills = ["tdd"]\n')
    assert pile.replaced(pile_path, claude_home.dir, apply=False) == (
        "compost replaces these, and they are still active here:\n  skills to set off in skillOverrides: tdd"
    )
    warning = capsys.readouterr().err
    assert re.fullmatch(
        f"warning: (cannot read )?{clone}/.claude-plugin/marketplace.json{message}; its installs are not checked\n",
        warning,
    )


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
        claude_config.read(claude_home.dir).enabled


def test_unreadable_settings_are_reported(claude_home):
    (claude_home.dir / "settings.json").write_text("{not json")
    with pytest.raises(claude_config.ClaudeConfigError, match="settings.json is not valid JSON"):
        claude_config.read(claude_home.dir)
