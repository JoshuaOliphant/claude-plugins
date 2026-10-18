# ruff: noqa  (one-off experiment script, kept as run)
# ABOUTME: Experiment script for mutant-diagnose (#114); see ../README.md. Paths come from MUTANT_WORK and COMPOST.
import os
from pathlib import Path

WORK = os.environ.get("MUTANT_WORK", "/tmp/mutant-diagnose")
SRC_ROOT = os.environ.get("COMPOST", "plugins/compost")
import json
import shutil
import subprocess

SRC = Path(SRC_ROOT).resolve()
PY = str(SRC / ".venv/bin/python")
tasks = json.load(open(f"{WORK}/tasks2.json"))
res = []
for t in tasks:
    orig = (SRC / t["module"]).read_text().splitlines()
    for arm in ("skill", "base"):
        d = Path(f"{WORK}/tasks2/t{t['n']:02d}/{arm}")
        src = (d / t["module"]).read_text().splitlines()
        fixed = [
            len(src) >= m["line"] and src[m["line"] - 1].strip() != m["after"].strip()
            for m in t["mutants"]
        ]
        W = Path(f"{WORK}/work2/grade")
        if W.exists():
            shutil.rmtree(W)
        shutil.copytree(d, W, ignore=shutil.ignore_patterns(".venv", "__pycache__"))
        if (W / "tests").exists():
            shutil.rmtree(W / "tests")
        shutil.copytree(SRC / "tests", W / "tests", ignore=shutil.ignore_patterns("__pycache__"))
        r = subprocess.run(
            [PY, "-m", "pytest", t["test"], "-q", "-p", "no:cacheprovider", "--no-cov"],
            cwd=W,
            capture_output=True,
            text=True,
        )
        extra = [
            f
            for f in subprocess.run(
                ["diff", "-rq", str(SRC / "scripts"), str(d / "scripts"), "-x", "__pycache__"],
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            if t["module"].split("/")[1] not in f
        ]
        res.append(
            dict(
                task=t["n"],
                arm=arm,
                module=t["module"],
                tests_ok=r.returncode == 0,
                fixed=fixed,
                exact=src == orig,
                other_changes=extra,
                last=r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "",
            )
        )
json.dump(res, open(f"{WORK}/grades2.json", "w"), indent=1)
for r in res:
    print(
        r["task"],
        r["arm"],
        "green" if r["tests_ok"] else "RED",
        r["fixed"],
        "exact" if r["exact"] else "differs",
        r["other_changes"] or "",
    )
