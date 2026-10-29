# ABOUTME: Grades one cross-module task (#173): puts the plugin's own tests back over the agent's tree and runs the whole suite.
# ABOUTME: Usage: grade.py <task> <tree>; green means no failure beyond the ones the unmutated tree already has (no .git here).
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path(os.environ.get("COMPOST", "plugins/compost")).resolve()
WORK = Path(os.environ.get("CM_WORK", "/tmp/cross-module"))
PY = str(SRC / ".venv/bin/python")
PLUGIN = "plugins/compost"


def main() -> None:
    name, tree = sys.argv[1], Path(sys.argv[2])
    task = next(t for t in json.loads((WORK / "built.json").read_text()) if t["task"] == name)
    suite = tree / PLUGIN / "tests"
    shutil.rmtree(suite, ignore_errors=True)
    shutil.copytree(WORK / "tests-aside" / name, suite)
    done = subprocess.run([PY, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", "--no-cov", "--tb=no", "-rf"],
                          cwd=tree / PLUGIN, capture_output=True, text=True, timeout=900, check=False)  # fmt: skip
    failed = sorted(
        line.split(" ")[1] for line in done.stdout.splitlines() if line.startswith("FAILED")
    )
    new = [f for f in failed if f not in task["baseline_failures"]]
    pristine = WORK / "tasks" / name / PLUGIN
    changed = subprocess.run(["diff", "-rq", str(pristine), str(tree / PLUGIN), "-x", "__pycache__", "-x", "tests", "-x", ".pytest_cache"],
                             capture_output=True, text=True, check=False).stdout.splitlines()  # fmt: skip
    print(
        json.dumps(
            {"task": name, "green": not new, "new_failures": new, "changed": changed}, indent=1
        )
    )


if __name__ == "__main__":
    main()
