# ruff: noqa  (one-off experiment script, kept as run)
# ABOUTME: Builds diagnose tasks from fix commits: the parent's plugin tree without skills, and the commit's tests held back (#169).
# ABOUTME: Env: REPO, PLUGIN, PY, FIX_WORK; reads candidates.json from select_fixes.py and symptoms.json beside this file.
import json
import os
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("REPO", ".")).resolve()
PLUGIN = os.environ.get("PLUGIN", "plugins/compost")
PY = os.environ.get("PY", str(REPO / PLUGIN / ".venv/bin/python"))
WORK = Path(os.environ.get("FIX_WORK", "/tmp/real-fix-diagnose"))


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout


def failing(tree: Path) -> list[str]:
    done = subprocess.run(
        [PY, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", "--no-cov", "--tb=no", "-rf"],
        cwd=tree / PLUGIN, capture_output=True, text=True, timeout=900, check=False,
    )  # fmt: skip
    return sorted(
        line.split(" ")[1] for line in done.stdout.splitlines() if line.startswith("FAILED")
    )


def main() -> None:
    symptoms = json.loads((HERE / "symptoms.json").read_text())
    candidates = {c["sha"][:7]: c for c in json.loads((WORK / "candidates.json").read_text())}
    tasks = []
    for number, short in enumerate(symptoms, start=1):
        candidate = candidates[short]
        tree = WORK / "tasks" / f"t{number}"
        shutil.rmtree(tree, ignore_errors=True)
        tree.mkdir(parents=True)
        archive = subprocess.run(
            ["git", "archive", candidate["parent"], PLUGIN],
            cwd=REPO,
            capture_output=True,
            check=True,
        )
        subprocess.run(["tar", "-x", "-C", str(tree)], input=archive.stdout, check=True)
        shutil.rmtree(
            tree / PLUGIN / "skills", ignore_errors=True
        )  # the arms must not find the skill by browsing
        task = {"task": f"t{number}", "sha": candidate["sha"], "parent": candidate["parent"], "tests": candidate["tests"],
                "sources": candidate["sources"], "symptom": symptoms[short]}  # fmt: skip
        hidden = WORK / "hidden" / task["task"]
        for test in candidate["tests"]:
            target = hidden / test
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(git("show", f"{candidate['sha']}:{test}"))
            (tree / test).write_text(
                target.read_text()
            )  # pristine copy to measure what the parent already fails
        task["preexisting_failures"] = failing(tree)
        for test in candidate["tests"]:
            (tree / test).write_text(
                git("show", f"{candidate['parent']}:{test}")
            )  # the agent sees the parent's tests
        tasks.append(task)
        print(
            task["task"],
            short,
            "preexisting failures:",
            len(task["preexisting_failures"]),
            flush=True,
        )
    (WORK / "tasks.json").write_text(json.dumps(tasks, indent=1))


if __name__ == "__main__":
    main()
