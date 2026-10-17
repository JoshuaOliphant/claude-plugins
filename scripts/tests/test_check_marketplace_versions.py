"""
ABOUTME: Tests for check_marketplace_versions.py: the pure drift rules, and git-tracked plugin dirs.
ABOUTME: drift() takes parsed JSON, so its rules run without files; one test builds a git repo.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_marketplace_versions as cmv  # noqa: E402


def catalog(**versions: str) -> dict:
    return {"plugins": [{"name": name, "version": v} for name, v in versions.items()]}


def test_in_sync_has_no_findings():
    findings = cmv.drift(catalog(a="1.0.0"), {"a": {"version": "1.0.0"}})
    assert not findings
    assert findings.lines() == []


def test_version_drift_names_both_versions():
    findings = cmv.drift(catalog(a="1.0.0"), {"a": {"version": "1.1.0"}})
    assert findings.mismatches == ["a: plugin.json=1.1.0 != marketplace.json=1.0.0"]


def test_registered_plugin_without_manifest_is_missing():
    findings = cmv.drift(catalog(a="1.0.0", b="2.0.0"), {"a": {"version": "1.0.0"}, "b": None})
    assert findings.missing == ["b: plugins/b/.claude-plugin/plugin.json not found"]
    assert findings.non_plugin == []


def test_registered_plugin_with_no_directory_is_missing():
    findings = cmv.drift(catalog(a="1.0.0"), {})
    assert findings.missing == ["a: plugins/a/.claude-plugin/plugin.json not found"]


def test_unregistered_plugin_is_reported():
    findings = cmv.drift(catalog(), {"new": {"version": "0.1.0"}})
    assert findings.unregistered == ["new"]


def test_directory_without_manifest_is_not_a_plugin():
    findings = cmv.drift(catalog(), {"stray": None})
    assert findings.non_plugin == ["stray"]
    assert findings.missing == []


def test_lines_group_every_kind_of_finding():
    findings = cmv.drift(
        catalog(a="1.0.0", gone="1.0.0"),
        {"a": {"version": "2.0.0"}, "new": {"version": "0.1.0"}, "stray": None},
    )
    text = "\n".join(findings.lines())
    assert "Missing plugin.json files:\n  - gone:" in text
    assert "Version drift" in text and "  - a: plugin.json=2.0.0" in text
    assert "not registered in marketplace.json (add a catalog entry):\n  - new" in text
    assert "aren't plugins (move them out of plugins/):\n  - stray" in text


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_untracked_plugin_dir_does_not_fail_the_check(tmp_path, capsys):
    """AC-1: leftovers of a retired plugin, never committed, don't count."""
    _write_json(tmp_path / ".claude-plugin" / "marketplace.json", catalog(a="1.0.0"))
    _write_json(tmp_path / "plugins" / "a" / ".claude-plugin" / "plugin.json", {"version": "1.0.0"})
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    (tmp_path / "plugins" / "retired" / "skills").mkdir(parents=True)
    (tmp_path / "plugins" / "retired" / "skills" / "leftover.md").write_text("x")

    assert cmv.main(tmp_path) == 0
    assert "OK: 1 plugin versions in sync." in capsys.readouterr().out


def test_tracked_dir_without_manifest_still_fails(tmp_path, capsys):
    _write_json(tmp_path / ".claude-plugin" / "marketplace.json", catalog())
    (tmp_path / "plugins" / "stray").mkdir(parents=True)
    (tmp_path / "plugins" / "stray" / "notes.md").write_text("x")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")

    assert cmv.main(tmp_path) == 1
    assert "  - stray (no .claude-plugin/plugin.json)" in capsys.readouterr().out


def test_registered_plugin_not_yet_committed_is_checked(tmp_path, capsys):
    """AGENTS.md runs this check before commit, when a new plugin is still untracked."""
    _write_json(tmp_path / ".claude-plugin" / "marketplace.json", catalog(new="0.1.0"))
    _git(tmp_path, "init", "-q")
    _write_json(
        tmp_path / "plugins" / "new" / ".claude-plugin" / "plugin.json", {"version": "0.1.0"}
    )

    assert cmv.main(tmp_path) == 0
    assert "OK: 1 plugin versions in sync." in capsys.readouterr().out


def test_deleted_but_still_tracked_dir_is_not_a_stray(tmp_path, capsys):
    """Retiring a plugin with rm -rf before git rm leaves its paths in the index."""
    _write_json(tmp_path / ".claude-plugin" / "marketplace.json", catalog())
    _write_json(
        tmp_path / "plugins" / "old" / ".claude-plugin" / "plugin.json", {"version": "1.0.0"}
    )
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    shutil.rmtree(tmp_path / "plugins" / "old")

    assert cmv.main(tmp_path) == 0
    assert "OK: 0 plugin versions in sync." in capsys.readouterr().out
