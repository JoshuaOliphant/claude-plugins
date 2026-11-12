"""
ABOUTME: Tests for check_version_bumps.py: the pure bump rule, and the two-PR collision in a real repo.
ABOUTME: unbumped() takes versions and the changed set, so its rule runs without git.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_version_bumps as cvb  # noqa: E402


@pytest.mark.parametrize(
    ("base", "head", "flagged"),
    [
        ("0.9.0", "0.9.1", False),
        ("0.9.0", "0.10.0", False),
        ("0.9.9", "1.0.0", False),
        ("0.9.0", "0.9.0", True),
        ("0.9.1", "0.9.0", True),
        ("0.10.0", "0.9.9", True),
    ],
    ids=["patch", "minor-numeric", "major", "same", "lower", "lower-numeric"],
)
def test_changed_plugin_needs_a_strictly_greater_version(base, head, flagged):
    found = cvb.unbumped({"a": base}, {"a": head}, {"a"}, "origin/main")
    assert bool(found) is flagged


def test_unbumped_line_names_both_versions():
    found = cvb.unbumped({"a": "0.9.1"}, {"a": "0.9.0"}, {"a"}, "origin/main")
    assert found == ["a: changed since origin/main, at 0.9.0, needs more than 0.9.1"]


def test_unchanged_plugin_is_not_flagged():
    assert cvb.unbumped({"a": "1.0.0"}, {"a": "1.0.0"}, set(), "origin/main") == []


def test_plugin_new_on_the_branch_is_skipped():
    assert cvb.unbumped({"new": None}, {"new": "0.1.0"}, {"new"}, "origin/main") == []


def test_version_that_is_not_semver_is_flagged():
    found = cvb.unbumped({"a": "1.0.0"}, {"a": "1.0.0-rc1"}, {"a"}, "origin/main")
    assert found == ["a: version 1.0.0-rc1 is not MAJOR.MINOR.PATCH"]


def test_base_version_that_is_not_semver_names_the_base():
    found = cvb.unbumped({"a": "1.0"}, {"a": "1.0.1"}, {"a"}, "origin/main")
    assert found == ["a: version 1.0 on origin/main is not MAJOR.MINOR.PATCH; fix it there"]


def test_head_manifest_without_a_version_says_so():
    found = cvb.unbumped({"a": "1.0.0"}, {"a": None}, {"a"}, "origin/main")
    assert found == ["a: plugin.json has no version"]


@pytest.mark.parametrize(
    ("version", "text", "expected"),
    [
        ("1.2.0", "# Changelog\n\n## [1.2.0] - 2026-01-01\n", []),
        ("1.2.0", "## [1.2.0]\n## [1.1.0]\n", []),
        ("1.2.0", "## [1.1.0] - 2026-01-01\n", ["a: CHANGELOG.md has no '## [1.2.0]' entry"]),
        ("1.2.0", "## [1.2.00]\n", ["a: CHANGELOG.md has no '## [1.2.0]' entry"]),
        ("1.2.0", "see ## [1.2.0] inline\n", ["a: CHANGELOG.md has no '## [1.2.0]' entry"]),
        ("1.2.0", None, ["a: no CHANGELOG.md"]),
    ],
    ids=["present", "among-others", "stale", "version-prefix", "not-a-heading", "no-file"],
)
def test_changed_plugin_needs_a_changelog_heading_for_its_version(version, text, expected):
    assert cvb.missing_entries({"a": version}, {"a": text}, {"a"}) == expected


def test_unchanged_plugin_needs_no_changelog_entry():
    assert cvb.missing_entries({"a": "1.0.0"}, {"a": None}, set()) == []


def test_plugin_without_a_version_is_left_to_the_bump_rule():
    assert cvb.missing_entries({"a": None}, {"a": None}, {"a"}) == []


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout


def _commit(root: Path, version: str, path: str, message: str, changelog: bool = True) -> None:
    (root / ".claude-plugin").mkdir(exist_ok=True)
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"plugins": [{"name": "a", "version": version}]})
    )
    manifest = root / "plugins" / "a" / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"version": version}))
    (root / "plugins" / "a" / path).write_text(message)
    if changelog:
        (root / "plugins" / "a" / "CHANGELOG.md").write_text(
            f"# Changelog\n\n## [{version}] - 2026-01-01\n"
        )
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", message)


def test_second_pr_bumping_to_the_same_version_fails_once_first_is_on_main(tmp_path, capsys):
    """AC-3: the #80/#81 collision. Both branch from one base and bump 0.8.1 -> 0.9.0."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _commit(tmp_path, "0.8.1", "base.md", "base")
    _git(tmp_path, "branch", "second")
    _commit(tmp_path, "0.9.0", "first.md", "first PR, merged")
    _git(tmp_path, "checkout", "-q", "second")
    _commit(tmp_path, "0.9.0", "second.md", "second PR")

    # Against its fork point the second branch looks bumped; against main it doesn't.
    fork_point = _git(tmp_path, "rev-parse", "main~1").strip()
    assert cvb.main(["--base", fork_point], root=tmp_path) == 0
    capsys.readouterr()

    assert cvb.main(["--base", "main"], root=tmp_path) == 1
    out = capsys.readouterr().out
    assert "a: changed since main, at 0.9.0, needs more than 0.9.0" in out

    _commit(tmp_path, "0.9.1", "second.md", "second PR, rebumped")
    assert cvb.main(["--base", "main"], root=tmp_path) == 0


def test_bump_without_a_changelog_entry_fails_until_one_is_added(tmp_path, capsys):
    """A branch that bumps and changes files still fails when CHANGELOG.md lacks the new version."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _commit(tmp_path, "0.8.1", "base.md", "base")
    _git(tmp_path, "checkout", "-q", "-b", "feature")
    _commit(tmp_path, "0.9.0", "feature.md", "feature", changelog=False)

    assert cvb.main(["--base", "main"], root=tmp_path) == 1
    assert "a: CHANGELOG.md has no '## [0.9.0]' entry" in capsys.readouterr().out

    _commit(tmp_path, "0.9.0", "feature.md", "feature, with entry")
    assert cvb.main(["--base", "main"], root=tmp_path) == 0
    assert "and a changelog entry" in capsys.readouterr().out


def test_changelog_only_edit_counts_as_a_shipped_change(tmp_path, capsys):
    """AC-2.4: CHANGELOG.md is shipped content, so editing it alone still needs a bump."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _commit(tmp_path, "0.8.1", "base.md", "base")
    _git(tmp_path, "checkout", "-q", "-b", "feature")
    changelog = tmp_path / "plugins" / "a" / "CHANGELOG.md"
    changelog.write_text(changelog.read_text() + "\nA note.\n")
    _git(tmp_path, "commit", "-qam", "edit the changelog only")

    assert cvb.main(["--base", "main"], root=tmp_path) == 1
    assert "a: changed since main, at 0.8.1, needs more than 0.8.1" in capsys.readouterr().out


def test_plugin_new_on_the_branch_still_needs_its_changelog_entry(tmp_path, capsys):
    """AC-2.3: a new plugin skips the bump rule but not the changelog rule."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "README.md").write_text("base")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _git(tmp_path, "checkout", "-q", "-b", "feature")
    _commit(tmp_path, "0.1.0", "skill.md", "new plugin", changelog=False)

    assert cvb.main(["--base", "main"], root=tmp_path) == 1
    assert "a: no CHANGELOG.md" in capsys.readouterr().out

    _commit(tmp_path, "0.1.0", "skill.md", "new plugin, with entry")
    assert cvb.main(["--base", "main"], root=tmp_path) == 0
