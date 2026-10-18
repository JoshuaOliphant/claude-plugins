# ABOUTME: Experiment script for mutant-diagnose (#114); see ../README.md. Paths come from MUTANT_WORK and COMPOST.
import os
from pathlib import Path

WORK = os.environ.get("MUTANT_WORK", "/tmp/mutant-diagnose")
SRC_ROOT = os.environ.get("COMPOST", "plugins/compost")
import json, shutil, subprocess, sys, os, re
from pathlib import Path

sys.path.insert(0, "scripts")
import thin

mod, test = sys.argv[1], sys.argv[2]
SRC = Path(SRC_ROOT).resolve()
W = Path(f"{WORK}/work2/{Path(mod).stem}")
if W.exists():
    shutil.rmtree(W)
shutil.copytree(
    SRC,
    W,
    ignore=shutil.ignore_patterns(".venv", "__pycache__", ".git", "node_modules", ".coverage"),
)
os.chdir(SRC)
orig = (SRC / mod).read_text()
ms = thin.mutants(mod, own=True)
rows = []
for i, m in enumerate(ms):
    if m["operator"] == "thin/ReplaceString":
        continue
    mut = thin.mutate(orig, m)
    if mut is None or mut == orig:
        continue
    a, b = orig.splitlines(), mut.splitlines()
    d = [(k + 1, a[k].strip(), b[k].strip()) for k in range(min(len(a), len(b))) if a[k] != b[k]]
    if not d:
        continue
    (W / mod).write_text(mut)
    r = subprocess.run(
        [
            str(SRC / ".venv/bin/python"),
            "-m",
            "pytest",
            test,
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
        rows.append(
            {
                "id": i,
                "operator": m["operator"],
                "line": d[0][0],
                "before": d[0][1],
                "after": d[0][2],
                "err": bool(
                    re.search(
                        r"(TypeError|NameError|AttributeError|SyntaxError|ImportError)", r.stdout
                    )
                ),
                "output": r.stdout[-1500:],
            }
        )
(W / mod).write_text(orig)
json.dump(rows, open(f"{WORK}/killed2_{Path(mod).stem}.json", "w"), indent=1)
print(mod, len(ms), len(rows))
