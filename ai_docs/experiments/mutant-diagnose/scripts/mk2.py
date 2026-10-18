# ABOUTME: Experiment script for mutant-diagnose (#114); see ../README.md. Paths come from MUTANT_WORK and COMPOST.
import os
from pathlib import Path

WORK = os.environ.get("MUTANT_WORK", "/tmp/mutant-diagnose")
SRC_ROOT = os.environ.get("COMPOST", "plugins/compost")
import json
import os
import random
import re
import shutil
import subprocess
import sys

sys.path.insert(0, "scripts")
import thin

SRC = Path(SRC_ROOT).resolve()
PY = str(SRC / ".venv/bin/python")
random.seed(114)
root = Path(f"{WORK}/tasks2")
shutil.rmtree(root, ignore_errors=True)
bad = re.compile(r"Is|IsNot|Lt|Gt|NumberReplacer|Invert|USub|BinaryOperator")
tasks = []


def run_tests(tree, test):
    r = subprocess.run(
        [PY, "-m", "pytest", test, "-q", "-p", "no:cacheprovider", "--no-cov", "--tb=line"],
        cwd=tree,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return r


for mod, test in (
    ("scripts/claude_config.py", "tests/test_claude_config.py"),
    ("scripts/skill_drift.py", "tests/test_skill_drift.py"),
):
    stem = Path(mod).stem
    rows = [
        x
        for x in json.load(open(f"{WORK}/killed2_{stem}.json"))
        if not bad.search(x["operator"]) and not x["err"]
    ]
    orig = (SRC / mod).read_text()
    ms = thin.mutants(mod, own=True)
    made = 0
    attempts = 0
    while made < 5 and attempts < 200:
        attempts += 1
        a, b = random.sample(rows, 2)
        if abs(a["line"] - b["line"]) < 30 or a["operator"] == b["operator"]:
            continue
        # apply both: line-padded mutation keeps line numbers, apply sequentially by mutating textual lines
        la, lb = a["line"] - 1, b["line"] - 1
        src = orig.splitlines()
        # mutate each separately then take the differing line(s)
        ma = thin.mutate(orig, ms[a["id"]]).splitlines()
        mb = thin.mutate(orig, ms[b["id"]]).splitlines()
        both = list(src)
        for k in range(len(src)):
            if ma[k] != src[k]:
                both[k] = ma[k]
            if mb[k] != src[k]:
                both[k] = mb[k]
        both_s = "\n".join(both) + "\n"
        only_a = "\n".join(ma) + "\n"
        only_b = "\n".join(mb) + "\n"
        n = len(tasks) + 1
        W = Path(f"{WORK}/work2/check")
        if W.exists():
            shutil.rmtree(W)
        shutil.copytree(
            SRC,
            W,
            ignore=shutil.ignore_patterns(
                ".venv", "__pycache__", ".git", "node_modules", ".coverage"
            ),
        )
        (W / mod).write_text(both_s)
        rb = run_tests(W, test)
        (W / mod).write_text(only_a)
        ra = run_tests(W, test)
        (W / mod).write_text(only_b)
        rbb = run_tests(W, test)
        if rb.returncode == 0 or ra.returncode == 0 or rbb.returncode == 0:
            continue  # both must be needed... each alone red = fixing the other leaves it red
        failed = [
            l.split("::", 1)[1].split(" ")[0]
            for l in rb.stdout.splitlines()
            if l.startswith("FAILED")
        ]
        for arm in ("skill", "base"):
            d = root / f"t{n:02d}" / arm
            shutil.copytree(
                SRC,
                d,
                ignore=shutil.ignore_patterns(
                    ".venv", "__pycache__", ".git", "node_modules", ".coverage", "tests", "evals"
                ),
            )
            (d / mod).write_text(both_s)
        tasks.append(
            {
                "n": n,
                "module": mod,
                "test": test,
                "mutants": [
                    {k: a[k] for k in ("id", "operator", "line", "before", "after")},
                    {k: b[k] for k in ("id", "operator", "line", "before", "after")},
                ],
                "failing": rb.stdout[-3000:],
            }
        )
        made += 1
json.dump(tasks, open(f"{WORK}/tasks2.json", "w"), indent=1)
print(len(tasks))
