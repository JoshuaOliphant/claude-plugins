# ABOUTME: Tests pile.py against real git repos: drift mapped to compost skills, pin moves, and NOTICE.
# ABOUTME: The upstream fixture serves a local repo as github.com, so clone and fetch both run offline.
import pile
import pytest
from conftest import commit, run_git


def test_load_reads_sources_with_their_feeds(pile_file):
    acme, own, watch = pile.load(pile_file)
    assert (acme.role, own.role, watch.role) == ("input", "frozen", "reference")
    assert acme.feeds["skills/to-tickets"] == ["slice", "spec"]
    assert own.feeds == {}


VALID = '[[source]]\nname = "x"\nrepo = "a/b"\nrole = "input"\nlicense = "MIT"\npin = "c"\n'
WITHOUT_PIN = VALID.replace('pin = "c"\n', "")
WITH_EXTRA = VALID + 'sha = "d"\n'


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (VALID.replace("input", "vendored"), "x: role must be one of input, frozen, reference, not 'vendored'"),
        (WITHOUT_PIN, r"source 1 \(x\): missing pin"),
        (WITH_EXTRA, r"source 1 \(x\): unknown field sha"),
        ("[[source]\n", "cannot read .*pile.toml"),
    ],
    ids=["unknown role", "missing field", "unknown field", "not toml"],
)
def test_load_names_what_is_wrong_with_the_file(tmp_path, text, message):
    path = tmp_path / "pile.toml"
    path.write_text(text)
    with pytest.raises(pile.PileError, match=message):
        pile.load(path)


def test_load_reports_a_missing_file(tmp_path):
    with pytest.raises(pile.PileError, match="cannot read .*absent.toml"):
        pile.load(tmp_path / "absent.toml")


@pytest.mark.parametrize(
    ("changed", "by_skill", "unmapped"),
    [
        (["skills/to-spec/SKILL.md"], {"spec": ["skills/to-spec/SKILL.md"]}, []),
        (["skills/to-spec"], {"spec": ["skills/to-spec"]}, []),
        (["skills/to-tickets/x.md"], {"slice": ["skills/to-tickets/x.md"], "spec": ["skills/to-tickets/x.md"]}, []),
        (["skills/to-spec-extra/SKILL.md", "README.md"], {}, ["skills/to-spec-extra/SKILL.md", "README.md"]),
    ],
)
def test_map_changes_matches_whole_path_segments(changed, by_skill, unmapped):
    feeds = {"skills/to-spec/": ["spec"], "skills/to-tickets": ["slice", "spec"]}
    assert pile.map_changes(changed, feeds) == (by_skill, unmapped)


def test_status_reports_nothing_new_then_changes_after_upstream_moves(pile_file, upstream):
    assert pile.render_status(pile.drift(pile.load(pile_file))) == (
        f"acme (acme/skills): nothing new since {pile.load(pile_file)[0].pin[:7]}"
    )
    head = commit(upstream, {"skills/to-spec/SKILL.md": "spec v2\n", "LICENSE": "MIT\n"}, "second")
    [item] = pile.drift(pile.load(pile_file))
    assert (item.head, item.by_skill, item.unmapped) == (head, {"spec": ["skills/to-spec/SKILL.md"]}, ["LICENSE"])
    status = pile.render_status([item])
    assert f"diffs: git -C {pile.CLONES / 'acme_skills'} diff" in status
    assert "  compost:spec\n    skills/to-spec/SKILL.md\n  feed no compost skill:\n    LICENSE" in status


def test_a_renamed_fed_skill_still_reports_under_the_skill_it_fed(pile_file, upstream):
    run_git(upstream, "mv", "skills/to-spec", "skills/spec-writer")
    commit(upstream, {"notes/my notes.md": "spaced\n"}, "rename and add a spaced path")
    [item] = pile.drift(pile.load(pile_file))
    assert item.by_skill == {"spec": ["skills/to-spec/SKILL.md"]}
    assert item.unmapped == ["notes/my notes.md", "skills/spec-writer/SKILL.md"]


def test_status_lists_unmapped_files_up_to_a_limit(pile_file):
    source = pile.load(pile_file)[0]
    unmapped = [f"docs/{n:02}.md" for n in range(pile.UNMAPPED_SHOWN + 2)]
    status = pile.render_status([pile.Drift(source, "f" * 40, {}, unmapped)])
    assert f"    docs/{pile.UNMAPPED_SHOWN - 1:02}.md\n    and 2 more" in status
    assert f"docs/{pile.UNMAPPED_SHOWN:02}.md" not in status


def test_compare_reports_a_pin_upstream_does_not_have(pile_file):
    with pytest.raises(pile.PileError, match="diff --name-only --no-renames -z 0000000 .* failed"):
        pile.git_compare("acme/skills", "0000000")


def test_git_missing_from_path_is_reported(monkeypatch):
    monkeypatch.setenv("PATH", "")
    with pytest.raises(pile.PileError, match="git not found on PATH"):
        pile.git("--version")


def test_advance_resolves_the_commit_and_moves_only_the_named_pin(pile_file, upstream):
    head = commit(upstream, {"skills/to-spec/SKILL.md": "spec v2\n"}, "second")
    before = pile_file.read_text()
    old, new = pile.advance(pile_file, "acme", head[:7])
    assert new == head
    assert pile_file.read_text() == before.replace(old, head)


def test_advance_refuses_a_commit_upstream_does_not_have(pile_file):
    with pytest.raises(pile.PileError, match="0000000 is not a commit in acme/skills"):
        pile.advance(pile_file, "acme", "0000000")


def test_advance_refuses_a_pin_written_in_another_form(pile_file):
    pile_file.write_text(pile_file.read_text().replace('pin = "aaaa', 'pin="aaaa'))
    with pytest.raises(pile.PileError, match="own's pin is not written as `pin = \"aaaa"):
        pile.advance(pile_file, "own", "c")


def test_advance_refuses_an_unknown_source(pile_file):
    with pytest.raises(pile.PileError, match="no source named 'nope' in pile.toml"):
        pile.advance(pile_file, "nope", "c")


def test_advance_refuses_a_pin_two_sources_share(pile_file):
    pile_file.write_text(pile_file.read_text().replace("bbbbbbbbbbbbbbbb", "aaaaaaaaaaaaaaaa"))
    with pytest.raises(pile.PileError, match="shared with another source"):
        pile.advance(pile_file, "own", "c")


def test_notice_lists_inputs_and_frozen_sources_but_not_references(pile_file):
    notice = pile.render_notice(pile.load(pile_file))
    assert "- acme: https://github.com/acme/skills (MIT), from " in notice
    assert "- own: https://github.com/me/old-plugins (MIT), from aaaaaaaaaaaa" in notice
    assert "else/skills" not in notice


def test_cli_status_prints_the_report(pile_file, capsys):
    assert pile.main(["--pile", str(pile_file), "status"]) == 0
    assert "acme (acme/skills): nothing new since" in capsys.readouterr().out


def test_cli_advance_prints_the_move(pile_file, upstream, capsys):
    old = pile.load(pile_file)[0].pin
    head = commit(upstream, {"README.md": "readme v2\n"}, "second")
    assert pile.main(["--pile", str(pile_file), "advance", "acme", head]) == 0
    assert capsys.readouterr().out == f"acme: {old[:7]} → {head[:7]}\n"


def test_cli_reports_errors_on_stderr(pile_file, capsys):
    assert pile.main(["--pile", str(pile_file), "advance", "nope", "c"]) == 1
    assert capsys.readouterr().err == "no source named 'nope' in pile.toml\n"


def test_cli_notice_writes_then_checks(pile_file, capsys):
    notice = pile_file.parent / "NOTICE"
    assert pile.main(["--pile", str(pile_file), "notice", "--check"]) == 1
    assert "is out of date; run `pile.py notice`" in capsys.readouterr().err
    assert pile.main(["--pile", str(pile_file), "notice"]) == 0
    assert notice.read_text() == pile.render_notice(pile.load(pile_file))
    assert pile.main(["--pile", str(pile_file), "notice", "--check"]) == 0
    notice.write_text("stale\n")
    assert pile.main(["--pile", str(pile_file), "notice", "--check"]) == 1
