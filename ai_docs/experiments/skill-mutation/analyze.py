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
    parser.add_argument(
        "--exclude-escaped", action="store_true", help="drop runs that read outside the sandbox"
    )
    args = parser.parse_args()

    rows = [json.loads(line) for line in (args.out / "results.jsonl").read_text().splitlines()]
    errors_path = args.out / "errors.jsonl"
    errors = (
        [json.loads(line) for line in errors_path.read_text().splitlines()]
        if errors_path.exists()
        else []
    )
    chunks = json.loads((args.out / "chunks.json").read_text())
    escaped = [r for r in rows if r.get("escaped")]
    if args.exclude_escaped:
        rows = [r for r in rows if not r.get("escaped")]
    cost = sum(r.get("cost_usd") or 0 for r in rows)
    print(
        f"scored runs {len(rows)}, infra errors {len(errors)}, escaped the sandbox {len(escaped)}"
    )
    print(f"subject cost ${cost:.2f} (judge cost not recorded)")

    passes: dict[tuple[str, int, int], list[bool]] = defaultdict(list)
    for row in rows:
        for i, ok in enumerate(row["verdict"]):
            passes[(row["variant"], row["case"], i)].append(ok)

    def rate(variant: str, case: int, i: int) -> float | None:
        seen = passes.get((variant, case, i))
        return sum(seen) / len(seen) if seen else None

    base = {(c, i): rate("baseline", c, i) for (v, c, i) in passes if v == "baseline"}
    live = {k: r for k, r in base.items() if r >= args.live}
    print(f"\nexpectations live at baseline: {len(live)}/{len(base)}")
    for (c, i), r in sorted(base.items()):
        print(
            f"  case {c} e{i + 1}: {r:.2f}{'' if (c, i) in live else '  (dead: cannot kill anything)'}"
        )

    verdicts = {}
    for variant, text in chunks.items():
        deltas = {
            (c, i): r - rate(variant, c, i)
            for (c, i), r in live.items()
            if rate(variant, c, i) is not None
        }
        if not deltas:
            continue
        killers = sorted((k for k, d in deltas.items() if d >= args.drop), key=lambda k: -deltas[k])
        gains = [k for k, d in deltas.items() if d <= -args.drop]
        verdicts[variant] = (text, killers, gains, sum(deltas.values()) / len(deltas))

    def line(variant: str) -> str:
        text, killers, gains, mean = verdicts[variant]
        by = ", ".join(f"c{c}e{i + 1}" for c, i in killers) or "-"
        up = f"  [HIGHER on {', '.join(f'c{c}e{i + 1}' for c, i in gains)}]" if gains else ""
        return f"  {variant:13} mean drop {mean:+.2f}  killed by {by:18} {text.strip()[:70]!r}{up}"

    controls = sorted(v for v in verdicts if v.startswith("ctrl-"))
    same = [v for v in controls if v.startswith("ctrl-same")]
    print("\nCONTROLS")
    for variant in controls:
        print(line(variant))
    false_kills = sum(bool(verdicts[v][1]) for v in same)
    print(f"  false-kill rate (identical copies killed): {false_kills}/{len(same)}")
    if "ctrl-no-skill" in verdicts and not verdicts["ctrl-no-skill"][1]:
        print("  WARNING: deleting the whole skill survives; these evals do not measure the skill")

    mutants = [v for v in verdicts if not v.startswith("ctrl-")]
    killed = [v for v in mutants if verdicts[v][1]]
    print(
        f"\nmutation score: {len(killed)}/{len(mutants)} = {len(killed) / max(len(mutants), 1):.0%}"
    )
    print("\nKILLED")
    for variant in killed:
        print(line(variant))
    print("\nSURVIVED (eval gap, or the line changes nothing)")
    for variant in sorted(set(mutants) - set(killed), key=lambda v: -verdicts[v][3]):
        print(line(variant))


if __name__ == "__main__":
    main()
