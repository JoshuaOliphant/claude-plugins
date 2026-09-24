# ABOUTME: Runs the review-changes workflow's node:test suite from pytest, so CI's one test command covers it.
# ABOUTME: The workflow is plain JavaScript that only runs inside Claude Code; the suite drives it with stub hooks.
import shutil
import subprocess

import pytest
from conftest import PLUGIN_ROOT


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed; the workflow suite needs it")
def test_review_changes_workflow_suite():
    result = subprocess.run(
        ["node", "--test", str(PLUGIN_ROOT / "tests" / "workflow.test.mjs")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
