# ABOUTME: Generates cross-module mutants for #173: mutate a helper module, keep mutants a different module's tests catch.
# ABOUTME: Usage: gen.py <helper path under plugin> <caller test path>; env COMPOST (plugin dir), CM_WORK (output dir).
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path(os.environ.get("COMPOST", "plugins/compost")).resolve()
WORK = Path(os.environ.get("CM_WORK", "/tmp/subtle"))
PY = str(SRC / ".venv/bin/python")
KEEP = re.compile(
    r"NumberReplacer|ReplaceComparisonOperator_(Lt|LtE|Gt|GtE)_(Lt|LtE|Gt|GtE)|ReplaceBinaryOperator_(Add|Sub|Mul|Div|FloorDiv|Mod)_(Add|Sub|Mul|Div|FloorDiv|Mod)|DropTerm|ReplaceAndWithOr|ReplaceOrWithAnd"
)

sys.path.insert(0, str(SRC / "scripts"))
import thin  # noqa: E402

helper, caller = sys.argv[1], sys.argv[2]
name = f"{Path(helper).stem}__{Path(caller).stem}"
tree = WORK / "gen" / name
shutil.rmtree(tree, ignore_errors=True)
shutil.copytree(
    SRC,
    tree,
    ignore=shutil.ignore_patterns(".venv", "__pycache__", ".git", "node_modules", ".coverage"),
)
os.chdir(SRC)
original = (SRC / helper).read_text()
rows = []
for index, mutant in enumerate(thin.mutants(helper, own=True)):
    if not KEEP.search(mutant["operator"]):
        continue
    mutated = thin.mutate(original, mutant)
    if mutated is None or mutated == original:
        continue
    before, after = original.splitlines(), mutated.splitlines()
    diff = [
        (n + 1, before[n].strip(), after[n].strip())
        for n in range(min(len(before), len(after)))
        if before[n] != after[n]
    ]
    if not diff:
        continue
    (tree / helper).write_text(mutated)
    done = subprocess.run([PY, "-m", "pytest", caller, "-q", "-x", "-p", "no:cacheprovider", "--no-cov", "--tb=short"],
                          cwd=tree, capture_output=True, text=True, timeout=120, check=False)  # fmt: skip
    if done.returncode == 1 and not re.search(
        r"(TypeError|NameError|AttributeError|SyntaxError|ImportError)", done.stdout
    ):
        rows.append({"id": index, "operator": mutant["operator"], "line": diff[0][0], "before": diff[0][1],
                     "after": diff[0][2], "output": done.stdout[-1500:]})  # fmt: skip
(tree / helper).write_text(original)
WORK.mkdir(parents=True, exist_ok=True)
(WORK / f"killed_{name}.json").write_text(json.dumps(rows, indent=1))
print(name, len(rows), flush=True)
