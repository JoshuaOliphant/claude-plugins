# ruff: noqa  (one-off experiment script, kept as run)
# ABOUTME: Grades one run: lays the hidden tests over the agent's tree and runs them; lists files changed against the pristine task.
# ABOUTME: Usage: grade.py <run>; env HW. Prints JSON {run, green, failed, changed}.
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("HW", "/tmp/hard-diagnose"))
PY = os.environ.get("PY", "/home/user/pt-venv/bin/python")


def main() -> None:
    run = sys.argv[1]
    task = run.split("-")[1]
    tree = WORK / "runs" / run
    changed = subprocess.run(
        [
            "diff",
            "-rq",
            str(HERE / "tasks" / task),
            str(tree),
            "-x",
            "__pycache__",
            "-x",
            ".pytest_cache",
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()
    shutil.rmtree(tree / "tests", ignore_errors=True)
    shutil.copytree(HERE / "hidden" / task / "tests", tree / "tests")
    done = subprocess.run(
        [PY, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", "--tb=line", "-rf"],
        cwd=tree,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    failed = [l for l in done.stdout.splitlines() if l.startswith("FAILED")]
    print(
        json.dumps(
            {"run": run, "green": done.returncode == 0, "failed": failed, "changed": changed}
        )
    )


if __name__ == "__main__":
    main()
