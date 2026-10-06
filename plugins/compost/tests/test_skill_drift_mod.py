# ABOUTME: Runs the skill-drift hooks module's engine tests and validation from pytest, so CI's one test command covers them.
# ABOUTME: Also checks the judgments file stays plain JSON after `export default`, since the live eval parses it.
import os
import shutil
import subprocess

import pytest
from conftest import PLUGIN_ROOT, skill_drift_judgments

needs_claude = pytest.mark.skipif(
    shutil.which("claude") is None and not os.environ.get("CI"),
    reason="the claude CLI runs the hooks module's tests; CI installs it, so there a missing CLI fails instead",
)


def test_judgments_are_plain_json_with_a_threshold_per_question():
    judgments = skill_drift_judgments()
    asked = {**judgments["turn"], **judgments["next_message"]}
    assert set(asked) == set(judgments["thresholds"]) == {"deviated", "missing_guidance", "corrected"}


@needs_claude
@pytest.mark.parametrize("command", ["validate", "test"])
def test_the_hooks_module_validates_and_passes_its_engine_tests(command):
    result = subprocess.run(
        ["claude", "plugin", command, str(PLUGIN_ROOT)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
