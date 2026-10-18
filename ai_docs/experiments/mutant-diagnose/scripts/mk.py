# ABOUTME: Experiment script for mutant-diagnose (#114); see ../README.md. Paths come from MUTANT_WORK and COMPOST.
import os
from pathlib import Path

WORK = os.environ.get("MUTANT_WORK", "/tmp/mutant-diagnose")
SRC_ROOT = os.environ.get("COMPOST", "plugins/compost")
import json, shutil, sys
from pathlib import Path

sys.path.insert(0, "scripts")
import thin

orig = Path("scripts/stop_guard.py").read_text()
ms = thin.mutants("scripts/stop_guard.py", own=True)
tasks = json.load(open(f"{WORK}/tasks.json"))
killed = {k["id"]: k for k in json.load(open(f"{WORK}/killed.json"))}
root = Path(f"{WORK}/tasks")
shutil.rmtree(root, ignore_errors=True)
for n, t in enumerate(tasks, 1):
    mut = thin.mutate(orig, ms[t["id"]])
    for arm in ("skill", "base"):
        d = root / f"t{n:02d}" / arm
        shutil.copytree(
            str(Path(SRC_ROOT).resolve()),
            d,
            ignore=shutil.ignore_patterns(
                ".venv", "__pycache__", ".git", "node_modules", ".coverage"
            ),
        )
        (d / "scripts/stop_guard.py").write_text(mut)
    out = killed[t["id"]]["output"]
    (root / f"t{n:02d}" / "symptom.txt").write_text(out)
    t["n"] = n
json.dump(tasks, open(f"{WORK}/tasks.json", "w"), indent=1)
