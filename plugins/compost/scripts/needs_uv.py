# ABOUTME: Lets a script whose typesafe-sdk dependency lives only in its PEP 723 header run under plain python3.
# ABOUTME: Importing it re-execs the running script with `uv run --script` when the SDK is missing, or exits 3 saying how.
import importlib.util
import os
import shutil
import sys

# Set on the re-exec, so a uv run that still lacks the SDK exits instead of re-execing forever.
MARKER = "COMPOST_UV_REEXEC"
EXIT_UNAVAILABLE = 3


def ensure(module="typesafe_sdk", argv=None, environ=None, which=shutil.which, execve=os.execve) -> None:
    """Returns when `module` imports. Otherwise replaces this process with the script in argv[0] under uv,
    which installs what its inline metadata declares; exits 3 when uv is missing or already ran it."""
    if importlib.util.find_spec(module) is not None:
        return
    argv = sys.argv if argv is None else argv
    environ = os.environ if environ is None else environ
    uv = which("uv")
    if uv and not environ.get(MARKER):
        execve(uv, [uv, "run", "--quiet", "--script", argv[0], *argv[1:]], {**environ, MARKER: "1"})
    cause = "uv ran it and it still did not import" if environ.get(MARKER) else "uv is not on PATH to install it"
    print(
        f"jev unavailable: {module} is not installed for {sys.executable} and {cause}. "
        f"Run it as `uv run {argv[0]}`, which reads the script's inline dependencies.",
        file=sys.stderr,
    )
    sys.exit(EXIT_UNAVAILABLE)


ensure()
