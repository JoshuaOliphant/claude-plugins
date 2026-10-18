# ABOUTME: Tests for the subject sandbox: escapes seen in results-116 are denied, in-sandbox calls pass, no parent context leaks in.
# ABOUTME: Run with `uv run --group dev pytest ai_docs/experiments/skill-mutation`.
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from sandbox_guard import blocked  # noqa: E402

GUARD = Path(__file__).parent / "sandbox_guard.py"


@pytest.fixture
def box(tmp_path, monkeypatch):
    """A sandbox laid out as mutate_skill.sandbox() makes it, with HOME and CLAUDE_PLUGIN_ROOT inside."""
    for d in ("project/knowledge/solutions", "home", "plugin/scripts"):
        (tmp_path / d).mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path / "plugin"))
    return tmp_path


# Every one of these left the sandbox in results-116 or is the same move by another tool.
ESCAPES = [
    ("Bash", {"command": "find / -name resolve_paths.py 2>/dev/null"}),
    ("Bash", {"command": "ls -la /root/.claude/plugins/synced/"}),
    ("Bash", {"command": "cat /home/user/claude-plugins/knowledge/solutions/critical-patterns.md"}),
    ("Bash", {"command": "grep -r feedback /tmp/claude/memory/team/silo"}),
    ("Bash", {"command": "cd ../../.. && ls"}),
    ("Bash", {"command": "ls ~/../../root"}),
    ("Bash", {"command": "python3 -c \"import os; print(os.listdir('/home'))\""}),
    ("Read", {"file_path": "/root/.claude/plugins/synced/compound-knowledge/SKILL.md"}),
    ("Read", {"file_path": "../../../etc/passwd"}),
    ("Grep", {"pattern": "critical", "path": "/home/user/claude-plugins"}),
    ("Glob", {"pattern": "/root/**/resolve_paths.py"}),
    ("Glob", {"pattern": "../../**/*.md"}),
    ("Glob", {"pattern": "*.md", "path": "/tmp/claude/memory"}),
]

# Calls the subject made inside the sandbox in results-116 (SANDBOX put back), plus the defaults.
INSIDE = [
    (
        "Bash",
        {
            "command": 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_paths.py" '
            '"$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; echo "exit=$?"'
        },
    ),
    ("Bash", {"command": "cat ~/.claude/compound-knowledge-registry.md 2>&1 | head -50"}),
    ("Bash", {"command": "ls -la ~/projects/skill-lab/knowledge/solutions 2>&1"}),
    ("Bash", {"command": "cd SANDBOX/project/knowledge/solutions && cat critical-patterns.md"}),
    ("Bash", {"command": "cd knowledge/solutions && ls .. && sed 's/a/b/' x.md"}),
    ("Bash", {"command": "find knowledge/solutions -type f -not -path '*/_archive/*' | head"}),
    ("Bash", {"command": "ls $HOME/.claude; grep -E 'pool|timeout' -r ."}),
    ("Read", {"file_path": "SANDBOX/project/knowledge/solutions/critical-patterns.md"}),
    ("Read", {"file_path": "knowledge/solutions/critical-patterns.md"}),
    ("Grep", {"pattern": "critical"}),
    ("Glob", {"pattern": "**/*.md"}),
    ("Glob", {"pattern": "*.md", "path": "~/projects/skill-lab"}),
    ("Agent", {"prompt": "search /root for the KB"}),
]


def resolve(tool_input: dict, box: Path) -> dict:
    return {k: v.replace("SANDBOX", str(box)) for k, v in tool_input.items()}


@pytest.mark.parametrize(("tool", "tool_input"), ESCAPES, ids=lambda x: str(x)[:50])
def test_escapes_are_blocked(box, tool, tool_input):
    assert blocked(tool, tool_input, str(box), str(box / "project")) is not None


@pytest.mark.parametrize(("tool", "tool_input"), INSIDE, ids=lambda x: str(x)[:50])
def test_calls_inside_the_sandbox_pass(box, tool, tool_input):
    assert blocked(tool, resolve(tool_input, box), str(box), str(box / "project")) is None


def test_the_hook_denies_through_claude_code_protocol(box):
    event = {"tool_name": "Bash", "tool_input": {"command": "find /"}, "cwd": str(box / "project")}
    out = subprocess.run(
        [sys.executable, str(GUARD), str(box)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert decision["permissionDecisionReason"].startswith("SANDBOX_GUARD: /")


def test_the_hook_stays_silent_on_an_allowed_call(box):
    event = {"tool_name": "Read", "tool_input": {"file_path": "x.md"}, "cwd": str(box / "project")}
    out = subprocess.run(
        [sys.executable, str(GUARD), str(box)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert out == ""


def test_a_child_claude_inherits_no_memory_or_extra_directories(monkeypatch, tmp_path):
    from mutate_skill import child_env

    monkeypatch.setenv("CLAUDE_COWORK_MEMORY_PATH_OVERRIDE", "/tmp/claude/memory")
    monkeypatch.setenv("CLAUDE_ADDITIONAL_DIRECTORIES", "/home/user/claude-plugins")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.test")
    env = child_env(tmp_path, {"CLAUDE_PLUGIN_ROOT": "x"})
    assert "CLAUDE_COWORK_MEMORY_PATH_OVERRIDE" not in env
    assert "CLAUDE_ADDITIONAL_DIRECTORIES" not in env
    assert env["ANTHROPIC_BASE_URL"] == "https://example.test"
    assert (env["HOME"], env["CLAUDE_PLUGIN_ROOT"]) == (str(tmp_path), "x")
