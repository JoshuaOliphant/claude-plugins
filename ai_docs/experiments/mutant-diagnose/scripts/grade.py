# ABOUTME: Experiment script for mutant-diagnose (#114); see ../README.md. Paths come from MUTANT_WORK and COMPOST.
import os
from pathlib import Path

WORK = os.environ.get("MUTANT_WORK", "/tmp/mutant-diagnose")
SRC_ROOT = os.environ.get("COMPOST", "plugins/compost")
import json
import subprocess

O = Path(SRC_ROOT).resolve()
orig = (O / "scripts/stop_guard.py").read_text().splitlines()
tasks = json.load(open(f"{WORK}/tasks.json"))
res = []
for t in tasks:
    for arm in ("skill", "base"):
        d = Path(f"{WORK}/tasks/t{t['n']:02d}/{arm}")
        src = (d / "scripts/stop_guard.py").read_text().splitlines()
        ln = t["line"]
        touched = len(src) >= ln and src[ln - 1] != None
        # mutated line text from rows
        mutated_line = t["after"]
        line_fixed = src[ln - 1].strip() != mutated_line.strip() if len(src) >= ln else False
        exact = src == orig
        diffs = [i + 1 for i, (a, b) in enumerate(zip(orig, src)) if a != b]
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
                "--no-cov",
                "-p",
                "no:cacheprovider",
            ],
            cwd=d,
            capture_output=True,
            text=True,
        )
        tests_ok = r.returncode == 0
        tests_untouched = (
            subprocess.run(
                ["diff", "-rq", str(O / "tests"), str(d / "tests"), "-x", "__pycache__"],
                capture_output=True,
                text=True,
            ).stdout.strip()
            == ""
        )
        other = [
            f
            for f in subprocess.run(
                ["diff", "-rq", str(O / "scripts"), str(d / "scripts"), "-x", "__pycache__"],
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            if "stop_guard.py" not in f
        ]
        res.append(
            dict(
                task=t["n"],
                arm=arm,
                op=t["operator"],
                line=ln,
                tests_ok=tests_ok,
                tests_untouched=tests_untouched,
                mutated_line_fixed=line_fixed,
                restored_exact=exact,
                remaining_diff_lines=diffs,
                other_script_changes=other,
            )
        )
json.dump(res, open(f"{WORK}/grades.json", "w"), indent=1)
for r in res:
    print(
        r["task"],
        r["arm"],
        "ok" if r["tests_ok"] else "RED",
        "line-fixed" if r["mutated_line_fixed"] else "LINE-NOT-FIXED",
        "exact" if r["restored_exact"] else f"diff@{r['remaining_diff_lines']}",
        "tests-ok" if r["tests_untouched"] else "TESTS-EDITED",
        r["other_script_changes"] or "",
    )
