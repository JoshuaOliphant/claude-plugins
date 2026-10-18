# ABOUTME: Tests for how mutate_skill.py fences in the subject: the lockdown settings, the /tmp/claude mount,
# ABOUTME: and the env. The sandbox itself is proven by the controls run in results-140/.
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import mutate_skill  # noqa: E402
from mutate_skill import child_env, hide_claude_tmp, lockdown  # noqa: E402


def test_lockdown_lets_bash_read_the_sandbox_and_no_dir_above_it(tmp_path):
    root = tmp_path / "mutation-sandbox-x"
    sandbox = lockdown(root)["sandbox"]
    reads = sandbox["filesystem"]
    assert reads["denyRead"] == ["/"]
    assert str(root) in reads["allowRead"]
    assert reads["allowWrite"] == [str(root)]
    # An allowed ancestor of root (/tmp, say) would show the sibling trials and the cloud memory dir.
    assert not [a for a in reads["allowRead"] if a != str(root) and root.is_relative_to(a)]
    assert sandbox["failIfUnavailable"] and not sandbox["allowUnsandboxedCommands"]


def test_lockdown_keeps_the_file_tools_in_the_working_dirs(tmp_path):
    assert lockdown(tmp_path)["permissions"] == {"blockReadsOutsideWorkingDirectories": True}


@pytest.mark.parametrize(
    ("platform", "euid", "has_tmp", "wrapped"),
    [
        ("linux", 0, True, True),
        ("linux", 1000, True, False),
        ("linux", 0, False, False),
        ("darwin", 0, True, False),
    ],
)
def test_hide_claude_tmp_wraps_only_where_it_can_mount(
    monkeypatch, platform, euid, has_tmp, wrapped
):
    monkeypatch.setattr(mutate_skill.sys, "platform", platform)
    monkeypatch.setattr(mutate_skill.os, "geteuid", lambda: euid)
    monkeypatch.setattr(mutate_skill.os.path, "isdir", lambda _: has_tmp)
    cmd = ["claude", "-p", "hi"]
    out = hide_claude_tmp(cmd)
    assert out[-3:] == cmd
    assert (out[0] == "unshare") is wrapped
    if wrapped:
        assert "mount -t tmpfs tmpfs /tmp/claude" in out[out.index("-c") + 1]


def test_a_child_claude_inherits_no_memory_or_extra_directories(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_COWORK_MEMORY_PATH_OVERRIDE", "/tmp/claude/memory")
    monkeypatch.setenv("CLAUDE_ADDITIONAL_DIRECTORIES", "/home/user/claude-plugins")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.test")
    env = child_env(tmp_path, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert "CLAUDE_COWORK_MEMORY_PATH_OVERRIDE" not in env
    assert "CLAUDE_ADDITIONAL_DIRECTORIES" not in env
    assert env["ANTHROPIC_BASE_URL"] == "https://example.test"
    assert (env["HOME"], env["CLAUDE_PLUGIN_ROOT"]) == (str(tmp_path), "x")
