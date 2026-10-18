# ruff: noqa  (one-off experiment script, kept as run)
# ABOUTME: Finds fix commits in a plugin's history whose test fails on the parent and passes on the commit (#169).
# ABOUTME: Each hit is a diagnose task: the parent tree is the bug, the commit's tests are the hidden grader.
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("REPO", ".")).resolve()
PLUGIN = os.environ.get("PLUGIN", "plugins/compost")
PY = os.environ.get("PY", str(REPO / PLUGIN / ".venv/bin/python"))
WORK = Path(os.environ.get("FIX_WORK", "/tmp/real-fix-diagnose"))
FIX = re.compile(r"^(fix|bug)", re.IGNORECASE)


def git(*args: str, cwd: Path = REPO) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout


def commits(rev: str) -> list[dict]:
    log = git(
        "log",
        rev,
        "--no-merges",
        "--format=%H%x09%P%x09%s",
        "--",
        f"{PLUGIN}/scripts",
        f"{PLUGIN}/tests",
    )
    rows = []
    for line in log.splitlines():
        sha, parents, subject = line.split("\t", 2)
        if FIX.match(subject) and len(parents.split()) == 1:
            rows.append({"sha": sha, "parent": parents, "subject": subject})
    return rows


def files(sha: str) -> tuple[list[str], list[str]]:
    names = git("diff-tree", "--no-commit-id", "--name-only", "-r", sha).split()
    tests = [n for n in names if n.startswith(f"{PLUGIN}/tests/test_") and n.endswith(".py")]
    sources = [n for n in names if n.startswith(f"{PLUGIN}/scripts/") and n.endswith(".py")]
    return tests, sources


def pytest(tree: Path, tests: list[str]) -> tuple[bool, str]:
    rel = [str(Path(t).relative_to(PLUGIN)) for t in tests]
    done = subprocess.run([PY, "-m", "pytest", *rel, "-q", "-p", "no:cacheprovider", "--no-cov", "--tb=line", "-x"],
                          cwd=tree / PLUGIN, capture_output=True, text=True, timeout=300)  # fmt: skip
    return done.returncode == 0, done.stdout[-1200:]


def checkout(sha: str, name: str) -> Path:
    tree = WORK / name
    shutil.rmtree(tree, ignore_errors=True)
    tree.parent.mkdir(parents=True, exist_ok=True)
    git("worktree", "add", "--detach", "-f", str(tree), sha)
    return tree


def main() -> None:
    rev = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    found = []
    for row in commits(rev):
        tests, sources = files(row["sha"])
        if not tests or not sources:
            continue
        parent = checkout(row["parent"], "parent")
        for test in tests:  # the commit's version of each test, on the parent's source
            (parent / test).write_text(git("show", f"{row['sha']}:{test}"))
        broken, output = pytest(parent, tests)
        fixed_tree = checkout(row["sha"], "fixed")
        fixed, _ = pytest(fixed_tree, tests)
        git("worktree", "remove", "--force", str(parent))
        git("worktree", "remove", "--force", str(fixed_tree))
        stat = git("diff", "--shortstat", row["parent"], row["sha"], "--", *sources).strip()
        issue = re.findall(r"#(\d+)", row["subject"])
        keep = (not broken) and fixed
        print(
            ("TASK " if keep else "skip "),
            row["sha"][:7],
            row["subject"][:80],
            "|",
            stat,
            flush=True,
        )
        if keep:
            found.append(
                {
                    **row,
                    "tests": tests,
                    "sources": sources,
                    "issue": issue,
                    "stat": stat,
                    "parent_output": output,
                }
            )
    out = WORK / "candidates.json"
    out.write_text(json.dumps(found, indent=1))
    print(len(found), "candidates ->", out)


if __name__ == "__main__":
    main()
