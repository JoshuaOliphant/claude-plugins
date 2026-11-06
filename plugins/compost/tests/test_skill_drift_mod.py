# ABOUTME: Runs compost's hooks module engine tests (skill-drift, architecture-review) and validation from pytest, so CI's one test command covers them.
# ABOUTME: Also checks the judgments file stays plain JSON and the hook's server, model and key constants match jevtools.core.
import os
import re
import shutil
import subprocess

import pytest
from conftest import PLUGIN_ROOT, skill_drift_judgments
from jevtools import core

needs_claude = pytest.mark.skipif(
    shutil.which("claude") is None and not os.environ.get("CI"),
    reason="the claude CLI runs the hooks module's tests; CI installs it, so there a missing CLI fails instead",
)


def test_judgments_are_plain_json_with_a_threshold_per_question():
    judgments = skill_drift_judgments()
    asked = {**judgments["turn"], **judgments["next_message"]}
    assert set(asked) == set(judgments["thresholds"]) == {"deviated", "missing_guidance", "corrected"}


def test_the_hook_targets_the_same_server_model_and_placeholder_key_as_core():
    """The hook cannot import core.py, so its copy of the Ollaya rules is held equal here."""
    source = (PLUGIN_ROOT / "hooks" / "skill-drift.ts").read_text()
    constants = dict(re.findall(r"^const (\w+) = '([^']*)'$", source, re.MULTILINE))
    assert constants["TYPESAFE_URL"] == core.TYPESAFE_URL
    assert constants["DEFAULT_MODEL"] == core.DEFAULT_MODEL
    assert constants["LOCAL_KEY"] == core.LOCAL_KEY
    for variable in (core.BASE_URL_VAR, core.MODEL_VAR, core.ENV_VAR):
        assert f"$.env.get('{variable}')" in source


@needs_claude
@pytest.mark.parametrize("command", ["validate", "test"])
def test_the_hooks_module_validates_and_passes_its_engine_tests(command):
    result = subprocess.run(
        ["claude", "plugin", command, str(PLUGIN_ROOT)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
