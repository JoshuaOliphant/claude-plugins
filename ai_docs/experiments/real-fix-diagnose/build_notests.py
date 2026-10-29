# ABOUTME: Makes the no-tests variant of the real-fix diagnose tasks (#171): same trees, tests/ removed, so the agent must build its own repro.
# ABOUTME: Env: FIX_WORK, PY, ARMS (default "skill base"; any arm but base reads the skill). Writes briefs for each <arm>-nt; trees go under runs/<arm>-nt/tN.
import json
import os
import shutil
from pathlib import Path

WORK = Path(os.environ.get("FIX_WORK", "/tmp/real-fix-diagnose"))
PLUGIN = os.environ.get("PLUGIN", "plugins/compost")
PY = os.environ.get("PY", "python3")

TEMPLATE = """You are fixing a bug in a copy of a Python plugin's source. No git history is available, and the plugin's test suite has been removed from this tree.

Tree: {tree}/{plugin}  (work only inside {tree})
Bug report, as a user wrote it:

{symptom}

{method}

Rules:
- Find the root cause in the code under scripts/ and fix it there. Your fix is graded by tests you cannot see, so decide for yourself how to know it works.
- You may run Python with: {py}  (for example `cd {tree}/{plugin} && {py} -c ...`; pytest is installed there too). Put any scratch files outside {tree}/{plugin}/scripts, and delete them before finishing.
- Do not look at any other directory under /tmp/real-fix-diagnose or at /home/user/claude-plugins (other than running the python interpreter and, if named above, the skill files); the answer is not there and doing so invalidates the run.
- When done, reply with: the root cause in two sentences, the files you changed, and how you checked the fix.
"""


def main() -> None:
    for arm in os.environ.get("ARMS", "skill base").split():
        for task in json.loads((WORK / "tasks.json").read_text()):
            name = task["task"]
            dst = WORK / "runs" / f"{arm}-nt" / name
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(WORK / "tasks" / name, dst)
            shutil.rmtree(dst / PLUGIN / "tests")
            method = (
                "Method: first read /tmp/real-fix-diagnose/skill/diagnose/SKILL.md and follow that skill's discipline for this bug."
                if arm != "base"
                else "Method: your choice."
            )
            brief = TEMPLATE.format(
                tree=dst, plugin=PLUGIN, symptom=task["symptom"], method=method, py=PY
            )
            out = WORK / "briefs" / f"{arm}-nt"
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}.md").write_text(brief)


if __name__ == "__main__":
    main()
