# ABOUTME: Tests `pile.py replaced`: finding superseded plugins and skills still active on a machine, and installs their
# ABOUTME: marketplace no longer lists, and acting on both, against a fake `claude` CLI and a throwaway ~/.claude.
import json

import claude_config
import pile
import pytest

REPLACES = pile.Replaces(
    plugins=("old@market", "proj@market", "synced-old@synced", "off@market", "absent@market"),
    skills=("tdd", "grill", "gone"),
)
INSTALLED = [
    {"id": "old@market", "scope": "user", "enabled": True},
    {"id": "proj@market", "scope": "project", "enabled": True},
    {"id": "synced-old@synced", "scope": "synced", "enabled": True},
    {"id": "off@market", "scope": "user", "enabled": False},
    {"id": "keep@market", "scope": "user", "enabled": True},
    {"id": "retired@market", "scope": "user", "enabled": False},
    {"id": "retired@market", "scope": "project", "enabled": True},
    {"id": "stray@unconfigured", "scope": "user", "enabled": True},
]
LISTED = ("old", "proj", "off", "keep")
ORPHANS = "retired@market (user scope), retired@market (project scope)"


@pytest.fixture
def machine(claude_home, tmp_path):
    """A ~/.claude with two superseded personal skills, and a `claude` CLI that lists INSTALLED, with the `market`
    marketplace's clone listing LISTED, and logs disables and uninstalls."""
    claude_dir = claude_home.dir
    (claude_dir / "skills" / "tdd").mkdir(parents=True)
    (claude_dir / "skills" / "grill").mkdir()
    (claude_dir / "skills" / "mine").mkdir()
    (claude_dir / "settings.json").write_text(json.dumps({"env": {"A": "1"}, "skillOverrides": {"grill": "off"}}))
    claude_home.install(*INSTALLED)
    claude_home.add_marketplace("market", *LISTED)
    pile_path = tmp_path / "pile.toml"
    pile_path.write_text(
        '[replaces]\nplugins = ["old@market", "synced-old@synced", "off@market"]\nskills = ["tdd", "grill", "gone"]\n'
    )
    return claude_dir, pile_path, claude_home.disabled


def test_find_active_separates_local_plugins_synced_plugins_skills_and_orphaned_installs():
    config = claude_config.Config(
        frozenset({"tdd", "grill"}), {"grill": "off"}, lambda: INSTALLED, lambda: {"market": frozenset(LISTED)}
    )
    active = pile.find_active(REPLACES, config)
    assert (active.plugins, active.synced, active.skills, active.orphaned) == (
        ["old@market", "proj@market"],
        ["synced-old@synced"],
        ["tdd"],
        [("retired@market", "user"), ("retired@market", "project")],
    )


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
        "  synced from claude.ai, turn off in your claude.ai settings: synced-old@synced\n"
        "Installed, but their marketplace no longer lists them:\n"
        f"  plugins to uninstall: {ORPHANS}"
    )
    assert (claude_dir / "settings.json").read_text() == before
    assert not log.exists()


def test_apply_disables_plugins_merges_overrides_into_settings_and_uninstalls_orphans(machine, claude_home):
    claude_dir, pile_path, log = machine
    report = pile.replaced(pile_path, claude_dir, apply=True)
    assert log.read_text() == "old@market\n"
    assert claude_home.uninstalled.read_text() == "retired@market user\nretired@market project\n"
    calls = ["list", "marketplace", "disable", "uninstall", "uninstall"]
    assert claude_home.calls.read_text() == "".join(f"{call} {claude_dir}\n" for call in calls)
    settings = json.loads((claude_dir / "settings.json").read_text())
    assert settings == {"env": {"A": "1"}, "skillOverrides": {"grill": "off", "tdd": "off"}}
    assert report.endswith(
        "disabled 1 plugins; set 1 skills off in skillOverrides; uninstalled 2 installs their marketplace dropped;"
        " still to do by hand: synced-old@synced on claude.ai. Restart Claude Code to apply."
    )
    assert "skills to set off" not in pile.replaced(pile_path, claude_dir, apply=False)


def test_apply_creates_settings_and_skips_the_hand_note_when_nothing_is_synced(machine):
    claude_dir, pile_path, _ = machine
    (claude_dir / "settings.json").unlink()
    pile_path.write_text('[replaces]\nplugins = []\nskills = ["tdd"]\n')
    report = pile.replaced(pile_path, claude_dir, apply=True, keep_orphans=True)
    assert json.loads((claude_dir / "settings.json").read_text()) == {"skillOverrides": {"tdd": "off"}}
    assert report.endswith("set 1 skills off in skillOverrides. Restart Claude Code to apply.")


def test_nothing_active_says_so_and_apply_does_nothing(machine, claude_home):
    claude_dir, pile_path, log = machine
    claude_home.install(*[plugin for plugin in INSTALLED if not plugin["id"].startswith("retired@")])
    pile_path.write_text('[replaces]\nplugins = ["off@market"]\nskills = ["gone"]\n')
    assert pile.replaced(pile_path, claude_dir, apply=True) == "Nothing compost replaces is active here."
    assert not log.exists()
    assert not claude_home.uninstalled.exists()


@pytest.mark.parametrize(
    ("flags", "uninstalled"),
    [(["--apply"], True), (["--apply", "--keep-orphans"], False), ([], False)],
    ids=["apply-uninstalls", "keep-orphans-uninstalls-nothing", "report-uninstalls-nothing"],
)
def test_orphaned_installs_are_reported_alone_and_uninstalled_only_on_apply(
    machine, claude_home, capsys, flags, uninstalled
):
    claude_dir, pile_path, log = machine
    pile_path.write_text('[replaces]\nplugins = ["off@market"]\nskills = ["gone"]\n')
    assert pile.main(["--pile", str(pile_path), "replaced", "--claude-dir", str(claude_dir), *flags]) == 0
    report = (
        "Nothing compost replaces is active here.\n"
        "Installed, but their marketplace no longer lists them:\n"
        f"  plugins to uninstall: {ORPHANS}\n"
    )
    if uninstalled:
        report += "disabled 0 plugins; set 0 skills off in skillOverrides; uninstalled 2 installs their marketplace"
        report += " dropped. Restart Claude Code to apply.\n"
    assert capsys.readouterr().out == report
    assert claude_home.uninstalled.exists() is uninstalled
    assert not log.exists()


def test_cli_replaced_prints_the_report_and_reports_config_errors(machine, capsys):
    claude_dir, pile_path, _ = machine
    assert pile.main(["--pile", str(pile_path), "replaced", "--claude-dir", str(claude_dir)]) == 0
    assert capsys.readouterr().out.startswith("compost replaces these")
    (claude_dir / "settings.json").write_text("{not json")
    assert pile.main(["--pile", str(pile_path), "replaced", "--claude-dir", str(claude_dir)]) == 1
    assert "settings.json is not valid JSON" in capsys.readouterr().err
