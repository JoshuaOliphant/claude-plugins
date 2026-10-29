# ABOUTME: Builds the seeded cross-module tasks for #173: a helper module carries one mutant, the symptom is written at its caller.
# ABOUTME: Env: COMPOST (plugin dir, with .venv), CM_WORK. Reads tasks.json and symptoms.json beside it. Tests are kept aside for grading.
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(os.environ.get("COMPOST", "plugins/compost")).resolve()
WORK = Path(os.environ.get("CM_WORK", "/tmp/subtle"))
PY = str(SRC / ".venv/bin/python")
PLUGIN = "plugins/compost"
IGNORE = shutil.ignore_patterns(
    ".venv", "__pycache__", ".git", "node_modules", ".coverage", ".pytest_cache", ".ruff_cache"
)

sys.path.insert(0, str(SRC / "scripts"))
import thin


def failing(tree: Path, *paths: str) -> list[str]:
    done = subprocess.run([PY, "-m", "pytest", *paths, "-q", "-p", "no:cacheprovider", "--no-cov", "--tb=no", "-rf"],
                          cwd=tree, capture_output=True, text=True, timeout=900, check=False)  # fmt: skip
    return sorted(
        line.split(" ")[1] for line in done.stdout.splitlines() if line.startswith("FAILED")
    )


def main() -> None:
    symptoms = (
        json.loads((HERE / "symptoms.json").read_text())
        if (HERE / "symptoms.json").exists()
        else {}
    )
    os.chdir(SRC)
    built = []
    mutants_by_helper: dict[str, list] = {}
    for task in json.loads((HERE / "tasks.json").read_text()):
        helper = task["helper"]
        mutants = mutants_by_helper.setdefault(helper, thin.mutants(helper, own=True))
        original = (SRC / helper).read_text()
        mutated = thin.mutate(original, mutants[task["id"]])
        tree = WORK / "tasks" / task["task"] / PLUGIN
        shutil.rmtree(tree.parent.parent, ignore_errors=True)
        shutil.copytree(SRC, tree, ignore=IGNORE)
        (tree / helper).write_text(original)
        baseline = failing(
            tree, "tests"
        )  # unmutated, no .git: the failures that are the environment's
        (tree / helper).write_text(mutated)
        red = failing(tree, "tests")
        tests_aside = WORK / "tests-aside" / task["task"]
        shutil.rmtree(tests_aside, ignore_errors=True)
        shutil.move(tree / "tests", tests_aside)
        shutil.rmtree(tree / "skills", ignore_errors=True)
        before = original.splitlines()
        after = mutated.splitlines()
        diff = [
            [n + 1, before[n], after[n]]
            for n in range(min(len(before), len(after)))
            if before[n] != after[n]
        ]
        row = {**task, "symptom": symptoms.get(task["task"], ""), "diff": diff, "baseline_failures": baseline,
               "mutant_failures": [f for f in red if f not in baseline]}  # fmt: skip
        built.append(row)
        print(
            task["task"],
            "baseline",
            len(baseline),
            "mutant adds",
            len(row["mutant_failures"]),
            flush=True,
        )
    (WORK / "built.json").write_text(json.dumps(built, indent=1))


if __name__ == "__main__":
    main()
