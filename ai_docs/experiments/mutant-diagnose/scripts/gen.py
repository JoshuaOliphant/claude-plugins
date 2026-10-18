# ruff: noqa  (one-off experiment script, kept as run)
# ABOUTME: Experiment script for mutant-diagnose (#114); see ../README.md. Paths come from MUTANT_WORK and COMPOST.
import os
from pathlib import Path

WORK = os.environ.get("MUTANT_WORK", "/tmp/mutant-diagnose")
SRC_ROOT = os.environ.get("COMPOST", "plugins/compost")
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, "scripts")
import thin

SRC = Path(SRC_ROOT).resolve()
W = Path(f"{WORK}/work/tree")
if W.exists():
    shutil.rmtree(W)
shutil.copytree(
    SRC, W, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".git", "node_modules")
)
os.chdir(SRC)
ms = thin.mutants("scripts/stop_guard.py", own=True)
orig = (SRC / "scripts/stop_guard.py").read_text()
out = []
for i, m in enumerate(ms):
    mut = thin.mutate(orig, m)
    if mut is None or mut == orig:
        continue
    (W / "scripts/stop_guard.py").write_text(mut)
    r = subprocess.run(
        [
            "uv",
            "run",
            "--with",
            "pytest",
            "python",
            "-m",
            "pytest",
            "tests/test_stop_guard.py",
            "-q",
            "-x",
            "-p",
            "no:cacheprovider",
            "--no-cov",
            "--tb=short",
        ],
        cwd=W,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if r.returncode == 1:
        out.append(
            {
                "id": i,
                "mutant": {k: m[k] for k in ("operator", "line", "occurrence", "args")},
                "output": r.stdout[-1800:],
            }
        )
(W / "scripts/stop_guard.py").write_text(orig)
json.dump(out, open(f"{WORK}/killed.json", "w"), indent=1)
print(len(ms), len(out))
