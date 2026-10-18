# ruff: noqa  (one-off experiment script, kept as run)
# ABOUTME: Experiment script for mutant-diagnose (#114); see ../README.md. Paths come from MUTANT_WORK and COMPOST.
import os
from pathlib import Path

WORK = os.environ.get("MUTANT_WORK", "/tmp/mutant-diagnose")
SRC_ROOT = os.environ.get("COMPOST", "plugins/compost")
import asyncio
import json
import sys

sys.path.insert(0, "scripts")
import thin
from jevtools import core
from typesafe_sdk import Choice, Noul

orig = Path("scripts/stop_guard.py").read_text()
ms = thin.mutants("scripts/stop_guard.py", own=True)
killed = json.load(open(f"{WORK}/killed.json"))
rows = []
for k in killed:
    m = ms[k["id"]]
    if m["operator"] == "thin/ReplaceString":
        continue
    mut = thin.mutate(orig, m)
    a, b = orig.splitlines(), mut.splitlines()
    d = [(i + 1, a[i].strip(), b[i].strip()) for i in range(min(len(a), len(b))) if a[i] != b[i]]
    if not d:
        continue
    ln = d[0][0]
    ctx = "\n".join(a[max(0, ln - 6) : ln + 4])
    first = (
        k["output"].split("FAILED")[-1].strip().splitlines()[0] if "FAILED" in k["output"] else ""
    )
    rows.append(
        {
            "id": k["id"],
            "operator": m["operator"],
            "line": ln,
            "before": d[0][1],
            "after": d[0][2],
            "ctx": ctx,
            "failed": first,
            "err": (
                "TypeError" in k["output"]
                or "NameError" in k["output"]
                or "AttributeError" in k["output"]
            ),
        }
    )


async def main():
    async with core.session() as jev:

        async def one(r):
            st = {
                "module": "stop_guard.py: a Claude Code Stop hook",
                "context": r["ctx"],
                "original_line": r["before"],
                "mutated_line": r["after"],
            }
            q = {
                "plausible": Noul(
                    instructions="Could a careful developer plausibly write `mutated_line` instead of `original_line` by mistake, so that a code reviewer would call it a realistic bug rather than an artificial mutation?"
                ),
                "mode": Choice(
                    instructions="How does the change in `mutated_line` fail at runtime?",
                    criteria={
                        "crash": "raises an exception on most inputs",
                        "wrong-logic": "runs but silently makes a wrong decision on some inputs",
                        "no-effect": "behaves the same or only changes a message or log",
                    },
                ),
            }
            a = await jev.ask("mutant-realism", st, q)
            r["plausible"] = round(a.noul("plausible"), 2)
            r["mode"] = a.choice("mode")

        await asyncio.gather(*[one(r) for r in rows])


asyncio.run(main())
json.dump(rows, open(f"{WORK}/rows.json", "w"), indent=1)
import collections

print(len(rows), collections.Counter(r["mode"] for r in rows))
for r in sorted(rows, key=lambda r: -r["plausible"])[:40]:
    print(
        r["id"],
        r["line"],
        r["operator"],
        r["plausible"],
        r["mode"],
        r["err"],
        "|",
        r["before"][:50],
        "=>",
        r["after"][:60],
    )
