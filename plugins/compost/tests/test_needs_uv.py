# ABOUTME: Tests that compost's Jev scripts run under plain python3: they re-exec under uv when typesafe-sdk is
# ABOUTME: missing, and exit 3 with one line saying how to run them when uv can't help, never with a traceback.
import os
import subprocess
import sys

import needs_uv
import pytest
from conftest import PLUGIN_ROOT

SCRIPTS = PLUGIN_ROOT / "scripts"
MISSING = "compost_no_such_module"


class Replaced(Exception):
    """Stands in for the process being replaced, which never returns."""


def recording(calls):
    def execve(path, args, env):
        calls.append((path, args, env))
        raise Replaced

    return execve


def test_an_importable_sdk_runs_in_process():
    calls = []
    needs_uv.ensure("json", ["jev.py", "list"], {}, lambda name: "/bin/uv", recording(calls))
    assert calls == []


def test_a_missing_sdk_re_execs_the_running_script_under_uv_with_its_arguments():
    calls = []
    with pytest.raises(Replaced):
        needs_uv.ensure(
            MISSING,
            ["scripts/jev.py", "status", "--input", "x"],
            {"HOME": "/h"},
            {"uv": "/bin/uv"}.get,
            recording(calls),
        )
    assert calls == [
        (
            "/bin/uv",
            ["/bin/uv", "run", "--quiet", "--script", "scripts/jev.py", "status", "--input", "x"],
            {"HOME": "/h", "COMPOST_UV_REEXEC": "1"},
        )
    ]


@pytest.mark.parametrize(
    "uv, environ, cause",
    [
        pytest.param(None, {}, "uv is not on PATH to install it", id="no-uv"),
        pytest.param(
            "/bin/uv", {"COMPOST_UV_REEXEC": "1"}, "uv ran it and it still did not import", id="already-re-execed"
        ),
    ],
)
def test_without_a_way_to_install_the_sdk_it_exits_3_in_one_line(uv, environ, cause, capsys):
    calls = []
    with pytest.raises(SystemExit) as stopped:
        needs_uv.ensure(MISSING, ["scripts/jev.py", "list"], environ, lambda name: uv, recording(calls))
    assert stopped.value.code == 3
    assert calls == []
    err = capsys.readouterr().err
    assert err.count("\n") == 1
    assert err.startswith(f"jev unavailable: {MISSING} is not installed for ")
    assert f" and {cause}. Run it as `uv run scripts/jev.py`" in err


def bare_python(*args, path):
    """Runs a script with -S, so the dev environment's typesafe-sdk is out of sight, as for a plain python3."""
    env = {key: value for key, value in os.environ.items() if key != "COMPOST_UV_REEXEC"}
    env["PATH"] = path
    return subprocess.run(
        [sys.executable, "-S", *args], capture_output=True, text=True, env=env, timeout=120, check=False
    )


@pytest.mark.parametrize("script", ["jev.py", "lint/jev_lint.py", "lint/run_eval.py"])
def test_each_jev_script_under_bare_python_without_uv_exits_3_without_a_traceback(script, tmp_path):
    ran = bare_python(str(SCRIPTS / script), path=str(tmp_path))
    assert ran.returncode == 3, ran.stderr
    assert "Traceback" not in ran.stderr
    assert f"Run it as `uv run {SCRIPTS / script}`" in ran.stderr


def test_jev_py_under_bare_python_re_execs_under_uv_and_lists_the_tools():
    ran = bare_python(str(SCRIPTS / "jev.py"), "list", path=os.environ["PATH"])
    assert ran.returncode == 0, ran.stderr
    assert "review-risk" in ran.stdout
