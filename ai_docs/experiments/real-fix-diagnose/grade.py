# ruff: noqa  (one-off experiment script, kept as run)
# ABOUTME: Grades an agent's tree for one task: the commit's tests laid over it, then its full suite (#169).
# ABOUTME: Usage: grade.py <task> <tree>; prints JSON with green (hidden tests pass), regressions, and files changed.
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("REPO", ".")).resolve()
PLUGIN = os.environ.get("PLUGIN", "plugins/compost")
PY = os.environ.get("PY", str(REPO / PLUGIN / ".venv/bin/python"))
WORK = Path(os.environ.get("FIX_WORK", "/tmp/real-fix-diagnose"))


def run_tests(tree: Path, *paths: str) -> tuple[bool, list[str]]:
    done = subprocess.run(
        [PY, "-m", "pytest", *paths, "-q", "-p", "no:cacheprovider", "--no-cov", "--tb=no", "-rf"],
        cwd=tree / PLUGIN, capture_output=True, text=True, timeout=900, check=False,
    )  # fmt: skip
    return done.returncode == 0, sorted(
        line.split(" ")[1] for line in done.stdout.splitlines() if line.startswith("FAILED")
    )


def changed_sources(task: dict, tree: Path) -> list[str]:
    """Plugin files differing from the parent's, found by diffing against a fresh archive of the parent."""
    pristine = WORK / "pristine" / task["task"]
    if not pristine.exists():
        pristine.mkdir(parents=True)
        archive = subprocess.run(
            ["git", "archive", task["parent"], PLUGIN], cwd=REPO, capture_output=True, check=True
        )
        subprocess.run(["tar", "-x", "-C", str(pristine)], input=archive.stdout, check=True)
    done = subprocess.run(["diff", "-rq", str(pristine / PLUGIN), str(tree / PLUGIN), "-x", ".venv", "-x", "skills",
                           "-x", "__pycache__", "-x", ".pytest_cache", "-x", ".coverage", "-x", ".ruff_cache"],
                          capture_output=True, text=True, check=False)  # fmt: skip
    return sorted(line for line in done.stdout.splitlines() if line)


def main() -> None:
    name, tree = sys.argv[1], Path(sys.argv[2])
    task = next(t for t in json.loads((WORK / "tasks.json").read_text()) if t["task"] == name)
    changes = changed_sources(task, tree)  # before the hidden tests overwrite anything
    suite = tree / PLUGIN / "tests"
    if not suite.exists():  # the no-tests variant (#171): put the parent's suite back before laying the hidden tests on it
        shutil.copytree(WORK / "tasks" / name / PLUGIN / "tests", suite)
    for test in task["tests"]:
        (tree / test).write_text((WORK / "hidden" / name / test).read_text())
    green, hidden_failures = run_tests(
        tree, *[str(Path(t).relative_to(PLUGIN)) for t in task["tests"]]
    )
    _, suite_failures = run_tests(tree, "tests")
    regressions = sorted(
        set(suite_failures) - set(hidden_failures) - set(task["preexisting_failures"])
    )
    print(json.dumps({"task": name, "green": green, "hidden_failures": hidden_failures,
                      "regressions": regressions, "changed": changes}, indent=1))  # fmt: skip


if __name__ == "__main__":
    main()
