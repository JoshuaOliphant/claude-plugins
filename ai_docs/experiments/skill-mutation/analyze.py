# ABOUTME: Reads mutate_skill.py's results.jsonl and reports which deletion mutants the evals killed and which survived.
# ABOUTME: Kill rule: some expectation that passes reliably at baseline drops by at least 0.5 (absolute) on the mutant.
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from mutate_skill import read_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument(
        "--live",
        type=float,
        help="reference pass rate for an expectation to count (default: --drop, the least that a kill needs)",
    )
    # Absolute, not relative: identical copies of the skill already differ by 0.4 on one
    # expectation at 5 trials, so a "lost half its rate" rule would kill 0.8 -> 0.4 on noise.
    parser.add_argument(
        "--drop", type=float, default=0.5, help="absolute pass-rate drop that kills a mutant"
    )
    parser.add_argument(
        "--exclude-escaped", action="store_true", help="drop runs that read outside the sandbox"
    )
    args = parser.parse_args()
    if args.live is None:
        args.live = args.drop

    rows = read_rows(args.out)
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
    # Runs from before the guard (#140) have no "denied" field; they count as 0 tries blocked.
    tried = sum(1 for r in rows if r.get("denied"))
    print(
        f"scored runs {len(rows)}, infra errors {len(errors)}, escaped the sandbox {len(escaped)}, "
        f"blocked trying to {tried}"
    )
    print(f"subject cost ${cost:.2f} (judge cost not recorded)")

    passes: dict[tuple[str, int, int], list[bool]] = defaultdict(list)
    for row in rows:
        for i, ok in enumerate(row["verdict"]):
            passes[(row["variant"], row["case"], i)].append(ok)

    # The reference is the baseline pooled with its byte-identical copies: one 5-trial baseline
    # is itself a noisy sample, and which identical arm got called "baseline" decided what was live.
    # Each identical copy is checked against the pool of the others, so it stays a fair noise test.
    same = sorted({v for v, _, _ in passes if v.startswith("ctrl-same")})
    reference_arms = ["baseline", *same]

    def rate(variants: list[str], case: int, i: int) -> float | None:
        seen = [ok for v in variants for ok in passes.get((v, case, i), [])]
        return sum(seen) / len(seen) if seen else None

    expectations = sorted({(c, i) for v, c, i in passes if v == "baseline"})
    reference = {k: rate(reference_arms, *k) for k in expectations}
    live = {k: r for k, r in reference.items() if r >= args.live}
    print(
        f"\nexpectations live in the reference ({' + '.join(reference_arms)}): {len(live)}/{len(reference)}"
    )
    for (c, i), r in sorted(reference.items()):
        print(
            f"  case {c} e{i + 1}: {r:.2f}{'' if (c, i) in live else '  (dead: cannot kill anything)'}"
        )

    verdicts = {}
    for variant, text in chunks.items():
        arms = [a for a in reference_arms if a != variant]
        deltas = {
            (c, i): rate(arms, c, i) - rate([variant], c, i)
            for (c, i) in live
            if rate([variant], c, i) is not None
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
    print("\nCONTROLS")
    for variant in controls:
        print(line(variant))
    false_kills = sum(bool(verdicts[v][1]) for v in same)
    print(f"  false-kill rate (identical copies killed): {false_kills}/{len(same)}")
    if "ctrl-no-skill" in verdicts and not verdicts["ctrl-no-skill"][1]:
        print("  WARNING: deleting the whole skill survives; these evals do not measure the skill")

    mutants = [v for v in verdicts if not v.startswith("ctrl-")]
    killed = [v for v in mutants if verdicts[v][1]]

    # Two identical copies cannot resolve a few-percent false-kill rate, so also estimate it:
    # if a mutant changed nothing, its k passes in n runs are Binomial(n, reference rate).
    def chance_kill(variant: str) -> float:
        survive = 1.0
        for c, i in live:
            n = len(passes.get((variant, c, i), []))
            p = rate([a for a in reference_arms if a != variant], c, i)
            cutoff = p - args.drop
            tail = sum(
                math.comb(n, k) * p**k * (1 - p) ** (n - k)
                for k in range(n + 1)
                if k / n <= cutoff + 1e-9
            )
            survive *= 1 - tail
        return 1 - survive

    expected = sum(chance_kill(v) for v in mutants)
    print(
        f"\nmutation score: {len(killed)}/{len(mutants)} = {len(killed) / max(len(mutants), 1):.0%}"
        f" (about {expected:.1f} kills expected by chance if no deletion mattered)"
    )
    print("\nKILLED")
    for variant in killed:
        print(line(variant))
    print("\nSURVIVED (eval gap, or the line changes nothing)")
    for variant in sorted(set(mutants) - set(killed), key=lambda v: -verdicts[v][3]):
        print(line(variant))


if __name__ == "__main__":
    main()
