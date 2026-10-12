# ABOUTME: Runs the memory-keeper hooks module's engine tests and validation from pytest,
# ABOUTME: so CI's one test command covers them.
import os
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

needs_claude = pytest.mark.skipif(
    shutil.which("claude") is None and not os.environ.get("CI"),
    reason="the claude CLI runs the hooks module's tests; CI installs it, so there a missing CLI fails instead",
)


@needs_claude
@pytest.mark.parametrize("command", ["validate", "test"])
def test_the_hooks_module_validates_and_passes_its_engine_tests(command):
    result = subprocess.run(
        ["claude", "plugin", command, str(PLUGIN_ROOT)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
