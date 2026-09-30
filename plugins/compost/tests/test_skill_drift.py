# ABOUTME: Tests `skill_drift.py`: grouping skill-drift hits into cross-session patterns on active skills, routing each
# ABOUTME: to its owner, splitting by skill version, and recording reviews. Runs against a throwaway ~/.claude and repo.
import json

import pytest
import skill_drift


def hit(**fields) -> dict:
    return {
        "skill": "compost:build",
        "kind": "deviated",
        "p": 0.9,
        "at": 1000,
        "session": "s1",
        "turn": "t1",
        "skill_hash": "v1",
        "prompt": "build issue #12",
        "evidence": "USER: build issue #12\nTOOL Write tests/test_new_suite.py",
        **fields,
    }


@pytest.fixture
def machine(tmp_path):
    """A ~/.claude with compost and plugin-dev enabled, one personal skill, one skill off, and a marketplace repo."""
    claude_dir = tmp_path / ".claude"
    (claude_dir / "skills" / "grilling").mkdir(parents=True)
    (claude_dir / "skills" / "grilling" / "SKILL.md").write_text("---\nname: grilling\n---\n")
    (claude_dir / "settings.json").write_text(
        json.dumps(
            {
                "enabledPlugins": {
                    "compost@oliphant": True,
                    "plugin-dev@official": True,
                    "stick-shift@oliphant": False,
                },
                "skillOverrides": {"compost:pause": "off"},
            }
        )
    )
    (claude_dir / "projects" / "-repo").mkdir(parents=True)
    (claude_dir / "projects" / "-repo" / "s1.jsonl").write_text("{}\n")
    repo = tmp_path / "repo"
    (repo / "plugins" / "compost" / "skills" / "build").mkdir(parents=True)
    (repo / "plugins" / "compost" / "skills" / "build" / "SKILL.md").write_text("---\nname: build\n---\n")

    def log(*hits: dict, name: str = "2026-09-29-s.jsonl") -> None:
        path = claude_dir / "skill-drift" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("".join(json.dumps(entry) + "\n" for entry in hits))

    return claude_dir, repo, log


def found(machine, **kwargs) -> dict:
    claude_dir, repo, _ = machine
    return skill_drift.patterns(claude_dir, repo, **kwargs)


@pytest.mark.parametrize(
    ("hits", "expected"),
    [
        ([hit(session="s1"), hit(session="s2", turn="t9")], [("compost:build", "deviated", 2)]),
        ([hit(session="s1"), hit(session="s1", turn="t2")], []),
        ([hit(session="s1"), hit(session="s2", kind="missing_guidance")], []),
        ([], []),
    ],
    ids=["two-sessions-make-a-pattern", "one-session-repeating-is-not", "kinds-are-not-pooled", "empty-log"],
)
def test_a_pattern_needs_the_same_kind_in_two_sessions(machine, hits, expected):
    machine[2](*hits)
    assert [(p["skill"], p["kind"], p["sessions"]) for p in found(machine)["patterns"]] == expected


def test_min_sessions_is_adjustable_and_a_missing_log_is_empty(machine):
    claude_dir, repo, log = machine
    assert skill_drift.patterns(claude_dir, repo) == {"patterns": [], "retired": {}, "unreadable": 0}
    log(hit())
    assert [p["sessions"] for p in found(machine, min_sessions=1)["patterns"]] == [1]


@pytest.mark.parametrize(
    "skill",
    ["stick-shift:build", "compost:pause", "grill-me", "never-installed:thing"],
    ids=["plugin-disabled", "skill-override-off", "personal-skill-removed", "plugin-not-installed"],
)
def test_hits_on_retired_skills_are_counted_and_left_out(machine, skill):
    machine[2](hit(skill=skill, session="s1"), hit(skill=skill, session="s2"))
    assert found(machine) == {"patterns": [], "retired": {skill: 2}, "unreadable": 0}


@pytest.mark.parametrize(
    ("skill", "owner", "file"),
    [
        ("compost:build", "repo", "plugins/compost/skills/build/SKILL.md"),
        ("grilling", "personal", "skills/grilling/SKILL.md"),
        ("plugin-dev:hook-development", "third-party", None),
    ],
    ids=["marketplace-plugin", "personal-skill", "someone-elses-plugin"],
)
def test_each_pattern_names_the_skills_owner_and_file(machine, skill, owner, file):
    claude_dir, _, log = machine
    log(hit(skill=skill, session="s1"), hit(skill=skill, session="s2"))
    (pattern,) = found(machine)["patterns"]
    expected = str((claude_dir / file).resolve()) if owner == "personal" else file
    assert (pattern["owner"], pattern["file"]) == (owner, expected)


def test_only_the_latest_skill_version_counts_and_earlier_hits_are_reported(machine):
    machine[2](
        hit(session="s1", skill_hash="v1", at=1),
        hit(session="s2", skill_hash="v1", at=2),
        hit(session="s3", skill_hash="v1", at=3),
        hit(session="s4", skill_hash="v2", at=4, kind="missing_guidance"),
        hit(session="s5", skill_hash="v2", at=5),
        hit(session="s6", skill_hash="v2", at=6),
    )
    (pattern,) = found(machine)["patterns"]
    assert (pattern["sessions"], pattern["earlier_versions"]) == (2, 3)
    assert {h["session"] for h in pattern["hits"]} == {"s5", "s6"}


def test_marked_hits_leave_later_runs(machine):
    claude_dir, _, log = machine
    log(hit(session="s1"), hit(session="s2"), hit(session="s3"))
    assert skill_drift.mark(claude_dir, ["s1:t1:compost:build:deviated"]) == 1
    assert found(machine)["patterns"][0]["sessions"] == 2
    skill_drift.mark(claude_dir, ["s2:t1:compost:build:deviated", "s1:t1:compost:build:deviated"])
    assert found(machine)["patterns"] == []
    assert json.loads((claude_dir / "skill-drift" / "reviewed.json").read_text()) == [
        "s1:t1:compost:build:deviated",
        "s2:t1:compost:build:deviated",
    ]


def test_hits_carry_their_id_evidence_and_transcript(machine):
    machine[2](hit(session="s1"), hit(session="s2"))
    claude_dir = machine[0]
    hits = found(machine)["patterns"][0]["hits"]
    assert [(h["id"], h["transcript"]) for h in hits] == [
        ("s1:t1:compost:build:deviated", str(claude_dir / "projects" / "-repo" / "s1.jsonl")),
        ("s2:t1:compost:build:deviated", None),
    ]
    assert hits[0]["evidence"].startswith("USER: build issue #12")


def test_unreadable_lines_are_counted_not_dropped_silently(machine):
    claude_dir, _, log = machine
    log(hit(session="s1"), hit(session="s2"))
    with (claude_dir / "skill-drift" / "2026-09-29-s.jsonl").open("a") as handle:
        handle.write("not json\n\n" + json.dumps({"skill": "x"}) + "\n")
    report = found(machine)
    assert (len(report["patterns"]), report["unreadable"]) == (1, 2)


def test_cli_prints_patterns_and_marks_reviews(machine, capsys, monkeypatch):
    claude_dir, repo, log = machine
    log(hit(session="s1"), hit(session="s2"))
    monkeypatch.chdir(repo)
    assert skill_drift.main(["--claude-dir", str(claude_dir), "patterns"]) == 0
    assert json.loads(capsys.readouterr().out)["patterns"][0]["file"] == "plugins/compost/skills/build/SKILL.md"
    assert skill_drift.main(["--claude-dir", str(claude_dir), "mark", "s1:t1:compost:build:deviated"]) == 0
    assert capsys.readouterr().out == "1 hits reviewed in all\n"


def test_cli_reports_unreadable_settings(machine, capsys):
    claude_dir, repo, _ = machine
    (claude_dir / "settings.json").write_text("{")
    assert skill_drift.main(["--claude-dir", str(claude_dir), "patterns", "--repo", str(repo)]) == 1
    assert "is not valid JSON" in capsys.readouterr().err
