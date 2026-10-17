# ABOUTME: Tests `pile.py replaced`: finding which superseded plugins and skills are still active on a machine,
# ABOUTME: and turning them off, against a fake `claude` CLI on PATH and a throwaway ~/.claude directory.
import json

import claude_config
import pile
import pytest

REPLACES = pile.Replaces(
    plugins=("old@market", "synced-old@synced", "off@market", "absent@market"), skills=("tdd", "grill", "gone")
)
INSTALLED = [
    {"id": "old@market", "scope": "user", "enabled": True},
    {"id": "synced-old@synced", "scope": "synced", "enabled": True},
    {"id": "off@market", "scope": "user", "enabled": False},
    {"id": "keep@market", "scope": "user", "enabled": True},
]


@pytest.fixture
def machine(claude_home, tmp_path):
    """A ~/.claude with two superseded personal skills, and a `claude` CLI that lists INSTALLED and logs disables."""
    claude_dir = claude_home.dir
    (claude_dir / "skills" / "tdd").mkdir(parents=True)
    (claude_dir / "skills" / "grill").mkdir()
    (claude_dir / "skills" / "mine").mkdir()
    (claude_dir / "settings.json").write_text(json.dumps({"env": {"A": "1"}, "skillOverrides": {"grill": "off"}}))
    claude_home.install(*INSTALLED)
    pile_path = tmp_path / "pile.toml"
    pile_path.write_text(
        '[replaces]\nplugins = ["old@market", "synced-old@synced", "off@market"]\nskills = ["tdd", "grill", "gone"]\n'
    )
    return claude_dir, pile_path, claude_home.disabled


def test_find_active_separates_local_plugins_synced_plugins_and_skills():
    enabled = {plugin["id"]: plugin["scope"] for plugin in INSTALLED if plugin["enabled"]}
    active = pile.find_active(REPLACES, claude_config.Config(enabled, frozenset({"tdd", "grill"}), {"grill": "off"}))
    assert (active.plugins, active.synced, active.skills) == (["old@market"], ["synced-old@synced"], ["tdd"])


def test_the_shipped_pile_names_what_compost_replaces():
    replaces = pile.load().replaces
    assert "superpowers@claude-plugins-official" in replaces.plugins
    assert "tdd" in replaces.skills


def test_report_without_apply_changes_nothing(machine):
    claude_dir, pile_path, log = machine
    before = (claude_dir / "settings.json").read_text()
    report = pile.replaced(pile_path, claude_dir, apply=False)
    assert report == (
        "compost replaces these, and they are still active here:\n"
        "  plugins to disable: old@market\n"
        "  skills to set off in skillOverrides: tdd\n"
        "  synced from claude.ai, turn off in your claude.ai settings: synced-old@synced"
    )
    assert (claude_dir / "settings.json").read_text() == before
    assert not log.exists()


def test_apply_disables_plugins_and_merges_overrides_into_settings(machine):
    claude_dir, pile_path, log = machine
    report = pile.replaced(pile_path, claude_dir, apply=True)
    assert log.read_text() == "old@market\n"
    settings = json.loads((claude_dir / "settings.json").read_text())
    assert settings == {"env": {"A": "1"}, "skillOverrides": {"grill": "off", "tdd": "off"}}
    assert report.endswith(
        "disabled 1 plugins; set 1 skills off in skillOverrides; still to do by hand: synced-old@synced on claude.ai."
        " Restart Claude Code to apply."
    )
    assert "skills to set off" not in pile.replaced(pile_path, claude_dir, apply=False)


def test_apply_creates_settings_and_skips_the_hand_note_when_nothing_is_synced(machine):
    claude_dir, pile_path, _ = machine
    (claude_dir / "settings.json").unlink()
    pile_path.write_text('[replaces]\nplugins = []\nskills = ["tdd"]\n')
    report = pile.replaced(pile_path, claude_dir, apply=True)
    assert json.loads((claude_dir / "settings.json").read_text()) == {"skillOverrides": {"tdd": "off"}}
    assert report.endswith("set 1 skills off in skillOverrides. Restart Claude Code to apply.")


def test_nothing_active_says_so_and_apply_does_nothing(machine):
    claude_dir, pile_path, log = machine
    pile_path.write_text('[replaces]\nplugins = ["off@market"]\nskills = ["gone"]\n')
    assert pile.replaced(pile_path, claude_dir, apply=True) == "Nothing compost replaces is active here."
    assert not log.exists()


def test_cli_replaced_prints_the_report_and_reports_config_errors(machine, capsys):
    claude_dir, pile_path, _ = machine
    assert pile.main(["--pile", str(pile_path), "replaced", "--claude-dir", str(claude_dir)]) == 0
    assert capsys.readouterr().out.startswith("compost replaces these")
    (claude_dir / "settings.json").write_text("{not json")
    assert pile.main(["--pile", str(pile_path), "replaced", "--claude-dir", str(claude_dir)]) == 1
    assert "settings.json is not valid JSON" in capsys.readouterr().err
