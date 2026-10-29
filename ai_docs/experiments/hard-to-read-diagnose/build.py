# ruff: noqa  (one-off experiment script, kept as run)
# ABOUTME: Builds one run directory (tree + brief) per task/arm/rep for the hard-to-read diagnose experiment (#187).
# ABOUTME: Env: HW (work dir, default /tmp/hard-diagnose), ARMS (default "skill base"), REPS (default "1 2"). Trees have no tests/.
import json
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("HW", "/tmp/hard-diagnose"))
PY = os.environ.get("PY", "/home/user/pt-venv/bin/python")
TASKS = os.environ.get("TASKS", " ".join(f"h{i}" for i in range(1, 11))).split()

TEMPLATE = """You are fixing a bug in a small Python project. Its test suite has been removed from this tree.

Tree: {tree}  (work only inside {tree})
Bug report, as a user wrote it:

{symptom}

{method}

Rules:
- Find the root cause and fix it where it lives. Your fix is graded by tests you cannot see, so decide for yourself how to know it works.
- Run Python with: {py}  (pytest is installed there). Put any scratch files in /tmp/scratch-{run}, not in the tree, and delete them before finishing.
- Do not look at any other directory under {work} or at /home/user/claude-plugins; the answer is not there and doing so invalidates the run.
- You cannot ask questions; nobody is available. When done, reply with: the root cause in two sentences, the files you changed, and how you checked the fix.
"""

METHOD = {
    "skill": "Method: use the compost:diagnose skill (the Skill tool) for this bug.",
    "base": "Method: your choice.",
}


def main() -> None:
    symptoms = json.loads((HERE / "symptoms.json").read_text())
    for arm in os.environ.get("ARMS", "skill base").split():
        for rep in os.environ.get("REPS", "1 2").split():
            for task in TASKS:
                run = f"{arm}-{task}-{rep}"
                tree = WORK / "runs" / run
                shutil.rmtree(tree, ignore_errors=True)
                shutil.copytree(HERE / "tasks" / task, tree)
                brief = TEMPLATE.format(
                    tree=tree, symptom=symptoms[task], method=METHOD[arm], py=PY, run=run, work=WORK
                )
                (WORK / "briefs").mkdir(parents=True, exist_ok=True)
                (WORK / "briefs" / f"{run}.md").write_text(brief)


if __name__ == "__main__":
    main()
