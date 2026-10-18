# ABOUTME: Lets a script whose typesafe-sdk dependency lives only in its PEP 723 header run under plain python3.
# ABOUTME: Importing it re-execs the running script with `uv run --script` when the SDK is missing, or exits 3 saying how.
import importlib
import os
import shutil
import subprocess
import sys

# Set on the re-exec, so a uv run that still lacks the SDK exits instead of re-execing forever.
MARKER = "COMPOST_UV_REEXEC"
EXIT_UNAVAILABLE = 3


def ensure(
    module="typesafe_sdk", argv=None, environ=None, which=shutil.which, run=subprocess.run, execve=os.execve
) -> None:
    """Returns when `module` imports. Otherwise replaces this process with the script in argv[0] under uv,
    which installs what its inline metadata declares; exits 3 when uv is missing, fails, or already ran it."""
    environ = os.environ if environ is None else environ
    try:
        importlib.import_module(module)
    except ImportError:
        pass
    else:
        environ.pop(MARKER, None)
        return
    argv = sys.argv if argv is None else argv
    uv = which("uv", path=environ.get("PATH"))
    if environ.get(MARKER):
        cause = "uv ran it and it still did not import"
    elif not uv:
        cause = "uv is not on PATH to install it"
    else:
        env = {**environ, MARKER: "1"}
        # Installing first keeps uv's own failures (offline, no matching Python) on exit 3 rather than its exit code.
        if run([uv, "sync", "--quiet", "--script", argv[0]], env=env, check=False).returncode == 0:
            execve(uv, [uv, "run", "--quiet", "--script", argv[0], *argv[1:]], env)
        cause = "uv could not install it"
    print(
        f"jev unavailable: {module} is not installed for {sys.executable} and {cause}. "
        f"Run it as `uv run {argv[0]}`, or make this call yourself.",
        file=sys.stderr,
    )
    sys.exit(EXIT_UNAVAILABLE)


ensure()
