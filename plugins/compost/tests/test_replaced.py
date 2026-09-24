# ABOUTME: Tests `pile.py replaced`: finding which superseded plugins and skills are still active on a machine,
# ABOUTME: and turning them off, against a fake `claude` CLI on PATH and a throwaway ~/.claude directory.
import json
import os

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
def machine(tmp_path, monkeypatch):
    """A ~/.claude with two superseded personal skills, and a `claude` CLI that lists INSTALLED and logs disables."""
    claude_dir = tmp_path / ".claude"
    (claude_dir / "skills" / "tdd").mkdir(parents=True)
    (claude_dir / "skills" / "grill").mkdir()
    (claude_dir / "skills" / "mine").mkdir()
    (claude_dir / "settings.json").write_text(json.dumps({"env": {"A": "1"}, "skillOverrides": {"grill": "off"}}))
    listing = tmp_path / "installed.json"
    listing.write_text(json.dumps(INSTALLED))
    log = tmp_path / "disabled.log"
    binary = tmp_path / "bin" / "claude"
    binary.parent.mkdir()
    binary.write_text(
        "#!/bin/sh\n"
        f'if [ "$2" = list ]; then cat "{listing}"; exit 0; fi\n'
        f'if [ "$2" = disable ]; then echo "$3" >> "{log}"; exit 0; fi\n'
        "exit 1\n"
    )
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", f"{binary.parent}{os.pathsep}{os.environ['PATH']}")
    pile_path = tmp_path / "pile.toml"
    pile_path.write_text(
        '[replaces]\nplugins = ["old@market", "synced-old@synced", "off@market"]\nskills = ["tdd", "grill", "gone"]\n'
    )
    return claude_dir, pile_path, log


@pytest.mark.parametrize(
    ("skills", "overrides", "expected"),
    [
        ({"tdd", "grill"}, {}, ["tdd", "grill"]),
        ({"tdd", "grill"}, {"grill": "off"}, ["tdd"]),
        ({"tdd", "grill"}, {"grill": "user-invocable-only"}, ["tdd", "grill"]),
        (set(), {}, []),
    ],
    ids=["both present", "one already off", "hidden is not off", "none installed"],
)
def test_find_active_separates_local_plugins_synced_plugins_and_skills(skills, overrides, expected):
    active = pile.find_active(REPLACES, INSTALLED, skills, overrides)
    assert (active.plugins, active.synced, active.skills) == (["old@market"], ["synced-old@synced"], expected)


def test_load_replaces_reads_the_table_and_tolerates_its_absence(tmp_path):
    path = tmp_path / "pile.toml"
    path.write_text('[replaces]\nplugins = ["a@b"]\n')
    assert pile.load_replaces(path) == pile.Replaces(("a@b",), ())
    path.write_text("")
    assert pile.load_replaces(path) == pile.Replaces((), ())
    path.write_text("[replaces\n")
    with pytest.raises(pile.PileError, match="cannot read"):
        pile.load_replaces(path)


def test_the_shipped_pile_names_what_compost_replaces():
    replaces = pile.load_replaces()
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


def test_a_machine_without_personal_skills(machine, tmp_path):
    _, pile_path, _ = machine
    empty = tmp_path / "empty-claude"
    empty.mkdir()
    assert pile.personal_skills(empty) == set()
    assert "skills to set off" not in pile.replaced(pile_path, empty, apply=False)


@pytest.mark.parametrize(
    ("path", "message"),
    [("", "the claude CLI is not on PATH"), ("failing", "claude plugin list --json failed: boom")],
)
def test_cli_problems_are_reported(machine, tmp_path, monkeypatch, path, message):
    claude_dir, pile_path, _ = machine
    if path:
        failing = tmp_path / "failing"
        failing.mkdir()
        (failing / "claude").write_text("#!/bin/sh\necho boom >&2\nexit 1\n")
        (failing / "claude").chmod(0o755)
        path = str(failing)
    monkeypatch.setenv("PATH", path)
    with pytest.raises(pile.PileError, match=message):
        pile.replaced(pile_path, claude_dir, apply=False)


def test_unreadable_settings_are_reported(machine):
    claude_dir, pile_path, _ = machine
    (claude_dir / "settings.json").write_text("{not json")
    with pytest.raises(pile.PileError, match="settings.json is not valid JSON"):
        pile.replaced(pile_path, claude_dir, apply=False)


def test_cli_replaced_prints_the_report(machine, capsys):
    claude_dir, pile_path, _ = machine
    assert pile.main(["--pile", str(pile_path), "replaced", "--claude-dir", str(claude_dir)]) == 0
    assert capsys.readouterr().out.startswith("compost replaces these")
