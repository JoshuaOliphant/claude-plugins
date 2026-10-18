# ABOUTME: Copies each cross-module task tree per arm and writes the agent briefs (#173). Env: CM_WORK, COMPOST.
import json
import os
import shutil
from pathlib import Path

WORK = Path(os.environ.get("CM_WORK", "/tmp/cross-module"))
PLUGIN = "plugins/compost"
PY = str(Path(os.environ.get("COMPOST", "plugins/compost")).resolve() / ".venv/bin/python")
BRIEF = """You are fixing a bug in a copy of a Python plugin's source. No git history is available, and the plugin's test suite has been removed from this tree.

Tree: {tree}/{plugin}  (work only inside {tree})
Bug report, as a user wrote it:

{symptom}

{method}

Rules:
- Find the root cause and fix it there; the cause may not be in the module the report is about. Your fix is graded by tests you cannot see, so decide for yourself how to know it works.
- You may run Python with: {py}  (for example `cd {tree}/{plugin} && {py} -c ...`; pytest is installed there too). Put any scratch files outside {tree}/{plugin}/scripts, and delete them before finishing.
- Do not look at any other directory under /tmp/cross-module or at /home/user/claude-plugins (other than running the python interpreter and, if named above, the skill files); the answer is not there and doing so invalidates the run.
- When done, reply with: the root cause in two sentences, the files you changed, and how you checked the fix.
"""
SKILL = "Method: first read /tmp/real-fix-diagnose/skill/diagnose/SKILL.md and follow that skill's discipline for this bug."
for arm in ("skill", "base"):
    for task in json.loads((WORK / "built.json").read_text()):
        dst = WORK / "runs" / arm / task["task"]
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(WORK / "tasks" / task["task"], dst)
        brief = BRIEF.format(
            tree=dst,
            plugin=PLUGIN,
            symptom=task["symptom"],
            py=PY,
            method=SKILL if arm == "skill" else "Method: your choice.",
        )
        out = WORK / "briefs" / arm
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{task['task']}.md").write_text(brief)
print("ok")
