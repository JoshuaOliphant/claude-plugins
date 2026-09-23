#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typesafe-sdk>=0.7"]
# ///
# ABOUTME: Runs the labeled AC-judge cases against the live Jev API and reports judgment and gate accuracy.
# ABOUTME: Compares each case judged alone against cases batched one-per-AC in a shared request.

import importlib.util
import sys
import time
from collections import defaultdict
from pathlib import Path

from typesafe_sdk import TypeSafeClient

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cases import CASES

_SPEC = importlib.util.spec_from_file_location(
    "ac_judge", HERE.parents[1] / "scripts" / "ac_judge.py"
)
ac_judge = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ac_judge)

CRITERIA = {ac.id: ac for ac in ac_judge.parse_acceptance_criteria((HERE / "spec.md").read_text())}


def run_batch(client, batch: list[dict]) -> tuple[dict[str, ac_judge.Verdict], float]:
    criteria = [CRITERIA[case["ac"]] for case in batch]
    evidence = {case["ac"]: {"result": "passed", "tests": case["tests"]} for case in batch}
    start = time.perf_counter()
    verdicts = ac_judge.judge(criteria, evidence, client, ac_judge.DEFAULT_THRESHOLD)
    elapsed = time.perf_counter() - start
    return {case["name"]: v for case, v in zip(batch, verdicts)}, elapsed


def one_per_ac_batches(cases: list[dict]) -> list[list[dict]]:
    by_ac = defaultdict(list)
    for case in cases:
        by_ac[case["ac"]].append(case)
    batches = []
    while any(by_ac.values()):
        batches.append([queue.pop(0) for queue in by_ac.values() if queue])
    return batches


def report(label: str, results: dict[str, ac_judge.Verdict], latencies: list[float]) -> None:
    judged = gated = 0
    print(f"\n== {label} ==")
    for case in CASES:
        v = results[case["name"]]
        judgment_ok = v.judgment == case["expected"]
        gate_ok = (v.verdict == "met") == (case["expected"] == "supports")
        judged += judgment_ok
        gated += gate_ok
        if judgment_ok and gate_ok:
            mark = "ok"
        elif judgment_ok:
            mark = "REVIEW"
        else:
            mark = "MISS"
        print(
            f"{mark:8} {case['name']:28} expected={case['expected']:12} "
            f"got={v.judgment:12} conf={v.confidence:.2f} verdict={v.verdict}"
        )
    n = len(CASES)
    print(f"judgment accuracy {judged}/{n}; gate accuracy (met iff supports) {gated}/{n}")
    print(f"requests {len(latencies)}; mean latency {sum(latencies) / len(latencies):.2f}s")


def main() -> None:
    with TypeSafeClient() as client:
        isolated, isolated_latency = {}, []
        for case in CASES:
            result, elapsed = run_batch(client, [case])
            isolated.update(result)
            isolated_latency.append(elapsed)
        batched, batched_latency = {}, []
        for batch in one_per_ac_batches(CASES):
            result, elapsed = run_batch(client, batch)
            batched.update(result)
            batched_latency.append(elapsed)
    report("isolated: one AC per request", isolated, isolated_latency)
    report("batched: one case per AC, shared request", batched, batched_latency)


if __name__ == "__main__":
    main()
