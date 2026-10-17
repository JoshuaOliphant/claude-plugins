# ABOUTME: Reads mutate_skill.py's results.jsonl and reports which deletion mutants the evals killed and which survived.
# ABOUTME: Kill rule: some expectation that passes reliably at baseline loses at least half its pass rate on the mutant.
import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument(
        "--live", type=float, default=0.66, help="baseline pass rate for an expectation to count"
    )
    parser.add_argument(
        "--drop", type=float, default=0.5, help="pass-rate drop that kills a mutant"
    )
    args = parser.parse_args()

    rows = [json.loads(line) for line in (args.out / "results.jsonl").read_text().splitlines()]
    chunks = json.loads((args.out / "chunks.json").read_text())
    passes: dict[tuple[str, int, int], list[bool]] = defaultdict(list)
    unjudged = 0
    for row in rows:
        if row["verdict"] is None:
            unjudged += 1
            continue
        for i, ok in enumerate(row["verdict"]):
            passes[(row["variant"], row["case"], i)].append(ok)

    def rate(variant: str, case: int, i: int) -> float | None:
        seen = passes.get((variant, case, i))
        return sum(seen) / len(seen) if seen else None

    base = {(c, i): rate("baseline", c, i) for (v, c, i) in passes if v == "baseline"}
    live = {k: r for k, r in base.items() if r >= args.live}
    print(f"rows {len(rows)}, unjudged {unjudged}")
    print(f"expectations live at baseline: {len(live)}/{len(base)}")
    for (c, i), r in sorted(base.items()):
        print(
            f"  case {c} e{i + 1}: {r:.2f}{'' if (c, i) in live else '  (dead: cannot kill anything)'}"
        )

    killed, survived = [], []
    for variant, text in chunks.items():
        deltas = {
            (c, i): r - (rate(variant, c, i) or 0.0)
            for (c, i), r in live.items()
            if rate(variant, c, i) is not None
        }
        if not deltas:
            continue
        killers = sorted((k for k, d in deltas.items() if d >= args.drop), key=lambda k: -deltas[k])
        gains = [k for k, d in deltas.items() if d <= -args.drop]
        entry = (variant, text, killers, gains, sum(deltas.values()) / len(deltas))
        (killed if killers else survived).append(entry)

    total = len(killed) + len(survived)
    print(f"\nmutation score: {len(killed)}/{total} = {len(killed) / max(total, 1):.0%}\n")
    print("KILLED")
    for variant, text, killers, _, mean in killed:
        names = ", ".join(f"c{c}e{i + 1}" for c, i in killers)
        print(f"  {variant:12} mean drop {mean:+.2f}  by {names:22} {text.strip()[:80]!r}")
    print("\nSURVIVED (eval gap, or the line changes nothing)")
    for variant, text, _, gains, mean in sorted(survived, key=lambda e: -e[4]):
        flag = (
            "  [mutant scored HIGHER on " + ", ".join(f"c{c}e{i + 1}" for c, i in gains) + "]"
            if gains
            else ""
        )
        print(f"  {variant:12} mean drop {mean:+.2f}  {text.strip()[:90]!r}{flag}")


if __name__ == "__main__":
    main()
