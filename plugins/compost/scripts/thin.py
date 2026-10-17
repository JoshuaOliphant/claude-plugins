# ABOUTME: Finds redundant tests for compost:thin: per-test coverage narrows the candidates, a full kill matrix
# ABOUTME: (every failing test per mutant, not the first) proves which ones no mutant needs. Stdlib only.
import argparse
import json
import os
import shlex
import sqlite3
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from contextlib import closing
from pathlib import Path


def covered_lines(contexts: dict) -> dict[str, set[tuple[str, int]]]:
    """Map each test node id to the (file, line) pairs it ran, from `coverage json --show-contexts`."""
    lines = defaultdict(set)
    for path, info in contexts["files"].items():
        for line, names in info["contexts"].items():
            for name in names:
                if name:  # the empty context is import time, which belongs to no test
                    lines[name.split("|")[0]].add((path, int(line)))
    return dict(lines)


def greedy_cover(sets: dict[str, set], covered: frozenset = frozenset()) -> list[str]:
    """The tests a greedy set cover keeps beyond `covered`: each pick adds the most not yet covered, ties by name."""
    universe = set().union(covered, *sets.values())
    covered, keep, pool = set(covered), [], dict(sets)
    while covered != universe:
        best = max(sorted(pool), key=lambda name: len(pool[name] - covered))
        keep.append(best)
        covered |= pool.pop(best)
    return keep


def candidates(contexts: dict) -> dict:
    """Tests whose lines are the same as, or inside, another test's. Leads only: a line run is not a line checked."""
    lines = covered_lines(contexts)
    groups = defaultdict(list)
    for name in sorted(lines):
        groups[frozenset(lines[name])].append(name)
    same = [names for names in groups.values() if len(names) > 1]
    inside = {}
    for small, names in groups.items():
        bigger = [big for big in groups if len(small) < len(big) and small <= big]
        if bigger:
            for name in names:
                inside[name] = groups[min(bigger, key=len)][0]
    return {
        "tests": len(lines),
        "same_lines": same,
        "inside": inside,
        "cover_keeps": len(greedy_cover(lines)),
        "candidates": sorted({name for names in same for name in names} | set(inside)),
    }


def mutants(module: str, cosmic_ray: list[str]) -> list[dict]:
    """Every mutation cosmic-ray would make in one module, read back from a throwaway session."""
    with tempfile.TemporaryDirectory() as tmp:
        config, session = Path(tmp) / "cr.toml", Path(tmp) / "session.sqlite"
        config.write_text(
            f'[cosmic-ray]\nmodule-path = "{module}"\ntimeout = 30.0\nexcluded-modules = []\ntest-command = "true"\n'
            '[cosmic-ray.distributor]\nname = "local"\n'
        )
        subprocess.run([*cosmic_ray, "init", str(config), str(session)], check=True, capture_output=True)
        with closing(sqlite3.connect(session)) as db:
            rows = db.execute(
                "SELECT operator_name, occurrence, start_pos_row FROM mutation_specs"
                " ORDER BY start_pos_row, operator_name, occurrence"
            ).fetchall()
    return [{"module": module, "operator": op, "occurrence": occ, "line": line} for op, occ, line in rows]


def junit_key(node_id: str) -> tuple[str, str]:
    """The (classname, name) pair pytest's junit report writes for a node id."""
    path, *scopes, name = node_id.split("::")
    return (".".join([path.removesuffix(".py").replace("/", "."), *scopes]), name)


def failing(test_command: list[str], tests: list[str], timeout: float) -> set[str] | None:
    """The tests among `tests` that fail, or None when the run produced no report (a crash or a timeout)."""
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "junit.xml"
        # A mutant the same size as the original, written within the same second, can otherwise run as its stale .pyc.
        env = {**os.environ, "PYTHONPYCACHEPREFIX": str(Path(tmp) / "pycache")}
        command = [*test_command, f"--junitxml={report}", *tests]
        try:
            subprocess.run(command, capture_output=True, timeout=timeout, env=env, check=False)
        except subprocess.TimeoutExpired:
            return None
        if not report.exists():
            return None
        by_key = {junit_key(test): test for test in tests}
        failed = set()
        for case in ET.parse(report).getroot().iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                failed.add(by_key.get((case.get("classname"), case.get("name"))))
        return failed - {None}


def kill_matrix(contexts: dict, only: list[str] | None, test_command: list[str], cosmic_ray: list[str],
                timeout: float, log=print) -> dict:  # fmt: skip
    """Run each mutant on a line the selected tests cover against every test covering that line; record each killer.

    Only the selected tests are mutated over every line they run, so only they can be judged from the result.
    """
    lines = covered_lines(contexts)
    selected = set(only) if only is not None else set(lines)
    on_line = defaultdict(set)
    for name, pairs in lines.items():
        for pair in pairs:
            on_line[pair].add(name)
    wanted = {pair for name in selected & set(lines) for pair in lines[name]}
    rows = []
    for module in sorted({path for path, _ in wanted}):
        source = Path(module).read_bytes()
        for mutant in mutants(module, cosmic_ray):
            if (module, mutant["line"]) not in wanted:
                continue
            covering = sorted(on_line[(module, mutant["line"])])
            try:
                applied = subprocess.run(
                    [*cosmic_ray, "apply", module, mutant["operator"], str(mutant["occurrence"])],
                    capture_output=True,
                    check=False,
                )
                killers = failing(test_command, covering, timeout) if applied.returncode == 0 else None
            finally:
                Path(module).write_bytes(source)
            if applied.returncode != 0:
                continue
            crashed = killers is None
            row = {**mutant, "covering": covering, "killers": covering if crashed else sorted(killers)}
            if crashed:
                row["crashed"] = True
            rows.append(row)
            log(f"{module}:{mutant['line']} {mutant['operator']}#{mutant['occurrence']} "
                f"killed by {len(row['killers'])}/{len(covering)}")  # fmt: skip
    return {"selected": sorted(selected & set(lines)), "mutants": rows}


def mutant_id(row: dict) -> str:
    return row.get("id") or f"{row['module']}:{row['line']} {row['operator']}#{row['occurrence']}"


def verdict(matrix: dict) -> dict:
    """Sort each selected test into keep, redundant (others kill all it kills), or kills-nothing.

    Tests outside the selection were mutated only where they overlap it, so they are always kept.
    """
    rows, selected = matrix["mutants"], set(matrix["selected"])
    kills = defaultdict(set)
    for row in rows:
        for test in row["covering"]:
            kills.setdefault(test, set())
        for test in row["killers"]:
            kills[test].add(mutant_id(row))
    killing = {test: ids for test, ids in kills.items() if ids}
    others = {test for test in killing if test not in selected}
    already = frozenset().union(*(killing[test] for test in others))
    keep = others | set(greedy_cover({t: ids for t, ids in killing.items() if t in selected}, already))
    tests = {}
    for test in sorted(selected & set(kills)):
        mine = kills[test]
        if not mine:
            tests[test] = {"verdict": "kills-nothing", "kills": 0}
            continue
        unique = sorted(m for m in mine if all(m not in kills[o] for o in killing if o != test))
        entry = {"verdict": "keep" if test in keep else "redundant", "kills": len(mine), "unique": unique}
        if test not in keep:
            over = [o for o in sorted(keep) if mine <= kills[o]]
            entry["subsumed_by"] = over[0] if over else None
        tests[test] = entry
    survived = sorted(mutant_id(row) for row in rows if not row["killers"])
    return {"mutants": len(rows), "survived": survived, "minimal": sorted(keep & selected), "tests": tests}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find redundant tests for compost:thin.")
    sub = parser.add_subparsers(dest="command", required=True)
    lead = sub.add_parser("candidates", help="tests whose covered lines equal, or sit inside, another test's")
    lead.add_argument("contexts", help="coverage json --show-contexts output")
    run = sub.add_parser("matrix", help="the full kill matrix over the lines the chosen tests cover")
    run.add_argument("contexts")
    chosen = run.add_mutually_exclusive_group()
    chosen.add_argument("--only", help="a candidates JSON; mutate only lines its candidates cover")
    chosen.add_argument("--tests", nargs="+", help="node ids; mutate only lines these tests cover")
    run.add_argument("--test-command", default="python -m pytest -q -p no:cacheprovider --no-cov")
    run.add_argument("--cosmic-ray", default="cosmic-ray", help="how to invoke cosmic-ray, e.g. 'uv run cosmic-ray'")
    run.add_argument("--timeout", type=float, default=300.0, help="seconds per mutant's test run")
    judge = sub.add_parser("verdict", help="keep, redundant, or kills-nothing for every test in a matrix")
    judge.add_argument("matrix")
    args = parser.parse_args(argv)

    if args.command == "candidates":
        result = candidates(json.loads(Path(args.contexts).read_text()))
    elif args.command == "matrix":
        only = json.loads(Path(args.only).read_text())["candidates"] if args.only else args.tests
        result = kill_matrix(
            json.loads(Path(args.contexts).read_text()),
            only,
            shlex.split(args.test_command),
            shlex.split(args.cosmic_ray),
            args.timeout,
            log=lambda line: print(line, file=sys.stderr, flush=True),
        )
    else:
        result = verdict(json.loads(Path(args.matrix).read_text()))
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
