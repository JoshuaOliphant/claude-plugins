# ABOUTME: Tests the plugin's SessionStart hook: silent without a harness, and one line of context saying whether the
# ABOUTME: project's harness is running and to query its telemetry. Runs the real hook script against fake status.sh.
import json
import os
import subprocess
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HOOK = PLUGIN_ROOT / "hooks" / "telemetry_nudge.sh"


def run_hook(project_dir):
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
    }
    return subprocess.run(["bash", str(HOOK)], capture_output=True, text=True, env=env, check=False)


def install_status(project_dir, script_body):
    harness = project_dir / ".claude" / "harness" / "observability"
    harness.mkdir(parents=True)
    (harness / "status.sh").write_text(f"#!/usr/bin/env bash\n{script_body}\n")


def test_without_a_harness_the_hook_adds_no_context(tmp_path):
    result = run_hook(tmp_path)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.mark.parametrize(
    ("status_script", "expected_state"),
    [
        pytest.param(
            """echo '{"installed": true, "running": true, "mode": "lite", "service": "shop", "services": {}}'""",
            "is running (lite mode, service shop)",
            id="running",
        ),
        pytest.param(
            """echo '{"installed": true, "running": false, "mode": "full", "service": "shop", "services": {}}'""",
            "is not running; start it with bash .claude/harness/observability/start.sh",
            id="down",
        ),
        pytest.param(
            "exit 1",
            "is not running; start it with bash .claude/harness/observability/start.sh",
            id="status-fails",
        ),
    ],
)
def test_with_a_harness_the_hook_says_whether_it_runs_and_to_query_it(
    tmp_path, status_script, expected_state
):
    install_status(tmp_path, status_script)
    result = run_hook(tmp_path)
    assert result.returncode == 0
    assert result.stderr == ""
    lines = result.stdout.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith(
        f"This project's observability harness {expected_state}. Query its traces"
    )
    assert "observability-query skill" in lines[0]


def test_hooks_json_runs_the_nudge_on_every_session_start():
    config = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text())
    groups = config["hooks"]["SessionStart"]
    assert [group.get("matcher") for group in groups] == [None]
    command = groups[0]["hooks"][0]["command"]
    assert command == 'bash "${CLAUDE_PLUGIN_ROOT}/hooks/telemetry_nudge.sh"'
    assert (PLUGIN_ROOT / "hooks" / "telemetry_nudge.sh").exists()
