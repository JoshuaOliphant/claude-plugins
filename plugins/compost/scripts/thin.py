# ABOUTME: Finds redundant tests for compost:thin: per-test coverage narrows the candidates, a full kill matrix
# ABOUTME: (every failing test per mutant, not the first) proves which ones no mutant needs. `survivors` runs the
# ABOUTME: mutants on a branch's changed lines for compost:verify. Mutant runs need pytest and cosmic-ray.
import argparse
import importlib.abc
import importlib.machinery
import json
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


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


class BaselineError(Exception):
    pass


class TimedOut:
    """What fork_runs returns for a run it killed at its deadline, so a hang is never read as a crash or a kill."""


TIMED_OUT = TimedOut()


def mutants(module: str) -> list[dict]:
    """Every mutation cosmic-ray would make in one module, in line order."""
    from cosmic_ray.commands.init import _all_work_items  # private, but it is how cosmic-ray init lists mutants

    found = [
        {"module": module, "operator": m.operator_name, "args": m.operator_args, "occurrence": m.occurrence,
         "line": m.start_pos[0]}
        for item in _all_work_items([Path(module)], {})
        for m in item.mutations
    ]  # fmt: skip
    return sorted(found, key=lambda m: (m["line"], m["operator"], m["occurrence"]))


def mutate(source: str, mutant: dict) -> str | None:
    """The mutated source, or None when cosmic-ray can't make it (its own AST walk crashes on a few)."""
    from cosmic_ray.mutating import mutate_code
    from cosmic_ray.plugins import get_operator

    try:
        return mutate_code(source, get_operator(mutant["operator"])(**mutant["args"]), mutant["occurrence"])
    except AttributeError:  # seen on a node parso builds without a `value`
        return None


class MutatedSource(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Serves one file's mutated source to whatever imports it, so the file on disk never changes."""

    def __init__(self, path: str, source: str):
        self.path, self.source = Path(path).resolve(), source

    def find_spec(self, name, path=None, target=None):
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is not None and spec.origin and Path(spec.origin).resolve() == self.path:
            spec.loader = self
            return spec
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        exec(compile(self.source, str(self.path), "exec"), module.__dict__)  # noqa: S102 - running the mutant is the point


def junit_key(node_id: str) -> tuple[str, str]:
    """The (classname, name) pair pytest's junit report writes for a node id; parameters may themselves hold `::`."""
    address, bracket, params = node_id.partition("[")
    path, *scopes, name = address.split("::")
    return (".".join([path.removesuffix(".py").replace("/", "."), *scopes]), name + bracket + params)


class Report:
    """What one run's junit report says about the tests it was asked to run."""

    def __init__(self, path: Path, tests: list[str]):
        by_key = {junit_key(test): test for test in tests}
        self.named, self.failed, self.strays = set(), set(), []
        for case in ET.parse(path).getroot().iter("testcase"):
            test = by_key.get((case.get("classname"), case.get("name")))
            broke = case.find("failure") is not None or case.find("error") is not None
            if test is not None:
                self.named.add(test)
                if broke:
                    self.failed.add(test)
            elif broke:  # a collection error, or a junit_prefix that changes every classname
                self.strays.append(f"{case.get('classname')}::{case.get('name')}")


def read_report(report: Path, tests: list[str]) -> Report | None:
    """The run's report, or None when it left none (a crash or a timeout)."""
    return Report(report, tests) if report.exists() else None


def run_child(pytest_args: list[str], tests: list[str], report: Path, module: str | None, source: str | None):
    """Run pytest in this forked process, with the mutant served from memory, then exit without returning."""
    import pytest

    quiet = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):  # an open stdin lets a mutant that reads it block until the timeout
        os.dup2(quiet, fd)
    sys.dont_write_bytecode = True
    # Run as a script, this directory is sys.path[0], and its modules would shadow the project's of the same name.
    sys.path[:] = [entry for entry in sys.path if Path(entry or ".").resolve() != SCRIPTS]
    if module is not None:
        sys.meta_path.insert(0, MutatedSource(module, source))
    # os._exit skips pytest's cleanup, so each child's tmp_path lives under a directory the parent removes.
    basetemp = report.with_suffix(".tmp")
    code = 1
    try:
        code = int(pytest.main([*pytest_args, f"--basetemp={basetemp}", f"--junitxml={report}", *tests]))
    finally:
        os._exit(code)


def fork_runs(
    jobs: list[tuple], pytest_args: list[str], timeout: float, workers: int
) -> list[Report | TimedOut | None]:
    """Run each (module, source, tests) job in a child forked from this already-warm process, `workers` at a time.

    Forking skips the interpreter start and pytest import that dominate a short test run, and serving the mutant
    from memory leaves the tree untouched, so the children can run side by side.
    """
    import pytest  # noqa: F401 - imported before forking so that no child pays for it

    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        pending, running = list(enumerate(jobs)), {}
        while pending or running:
            while pending and len(running) < workers:
                index, (module, source, tests) = pending.pop(0)
                report = Path(tmp) / f"{index}.xml"
                pid = os.fork()
                if pid == 0:
                    run_child(pytest_args, tests, report, module, source)
                running[pid] = (index, tests, report, time.monotonic() + timeout)
            for pid, (index, tests, report, deadline) in list(running.items()):
                done, _ = os.waitpid(pid, os.WNOHANG)
                if not done and time.monotonic() < deadline:
                    continue
                if not done:
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                results[index] = read_report(report, tests) if done else TIMED_OUT
                del running[pid]
            time.sleep(0.005)
    return [results[index] for index in range(len(jobs))]


def check_baseline(tests: list[str], pytest_args: list[str], timeout: float) -> None:
    """Raise unless the unmutated tests all pass and the report names each one.

    Under a broken setup every run fails, and every mutant would read as killed.
    """
    [baseline] = fork_runs([(None, None, tests)], pytest_args, timeout, 1)
    if not isinstance(baseline, Report):
        raise BaselineError("the unmutated tests left no report: check the interpreter has pytest and the tests import")
    if baseline.strays:
        raise BaselineError(f"the report names a failure no selected test matches: {baseline.strays[0]}")
    if baseline.failed:
        raise BaselineError(f"{len(baseline.failed)} tests fail unmutated, e.g. {min(baseline.failed)}: fix them first")
    if missing := set(tests) - baseline.named:
        raise BaselineError(
            f"the report never names {min(missing)}: check junit_prefix, and that thin runs from the rootdir"
        )


def kill_matrix(contexts: dict, only: list[str] | None, pytest_args: list[str], timeout: float, workers: int,
                log=print) -> dict:  # fmt: skip
    """Run each mutant on a line the selected tests cover against every test covering that line; record each killer.

    Only the selected tests are mutated over every line they run, so only they can be judged from the result. The
    tests must pass unmutated first: under a broken setup every run fails, every test kills every mutant, and the
    verdict would call all but one of them redundant.
    """
    lines = covered_lines(contexts)
    selected = set(only) if only is not None else set(lines)
    on_line = defaultdict(set)
    for name, pairs in lines.items():
        for pair in pairs:
            on_line[pair].add(name)
    wanted = {pair for name in selected & set(lines) for pair in lines[name]}
    everyone = sorted({test for pair in wanted for test in on_line[pair]})
    if not everyone:  # with no node ids, pytest would run the whole suite
        return {"selected": sorted(selected & set(lines)), "mutants": []}
    check_baseline(everyone, pytest_args, timeout)
    jobs, made = [], []
    for module in sorted({path for path, _ in wanted}):
        source = Path(module).read_text()
        for mutant in mutants(module):
            if (module, mutant["line"]) not in wanted:
                continue
            mutated = mutate(source, mutant)
            if mutated is None:
                continue
            covering = sorted(on_line[(module, mutant["line"])])
            jobs.append((module, mutated, covering))
            made.append({k: v for k, v in mutant.items() if k != "args"} | {"covering": covering})
    rows = []
    for row, report in zip(made, fork_runs(jobs, pytest_args, timeout, workers)):
        crashed = not isinstance(report, Report) or bool(report.strays)  # a broken run kills every covering test
        row["killers"] = row["covering"] if crashed else sorted(report.failed)
        if crashed:
            row["crashed"] = True
        rows.append(row)
        log(f"{row['module']}:{row['line']} {row['operator']}#{row['occurrence']} "
            f"killed by {len(row['killers'])}/{len(row['covering'])}")  # fmt: skip
    return {"selected": sorted(selected & set(lines)), "mutants": rows}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def changed_lines(base: str, paths: list[str]) -> dict[str, set[int]]:
    """The Python lines under `paths` that differ from `base` in the working tree, untracked files whole."""
    changed, current = defaultdict(set), None
    for line in git("diff", "-U0", "--relative", "--no-color", base, "--", *paths).splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None  # None: the file was deleted
        elif line.startswith("@@") and current and current.endswith(".py"):
            new = line.split()[2].lstrip("+").split(",")
            start, count = int(new[0]), int(new[1]) if len(new) > 1 else 1
            changed[current].update(range(start, start + count))
    for path in git("ls-files", "--others", "--exclude-standard", "--", *paths).splitlines():
        if path.endswith(".py"):
            changed[path].update(range(1, len(Path(path).read_text().splitlines()) + 1))
    return {path: lines for path, lines in changed.items() if lines}


def first_difference(source: str, mutated: str) -> str:
    """The first line the mutant changes, stripped; a mutant can add or drop lines, so line numbers can't pick it."""
    pairs = zip(source.splitlines(), mutated.splitlines() + [""] * len(source.splitlines()))
    return next((new.strip() for old, new in pairs if old != new), "")


def survivors(contexts: dict, changed: dict[str, set[int]], pytest_args: list[str], timeout: float, workers: int,
              log=print) -> dict:  # fmt: skip
    """Run each mutant on a changed line, stopping at the first failing test, and report the ones no test notices.

    A changed line no test runs, such as a module constant or a default argument that runs only at import,
    is tried against the whole suite, since coverage credits import-time lines to no test.
    """
    on_line = defaultdict(set)
    for name, pairs in covered_lines(contexts).items():
        for path, number in pairs:
            on_line[(os.path.relpath(path), number)].add(name)
    everyone = sorted({name for names in on_line.values() for name in names})
    jobs, made = [], []
    for module in sorted(changed):
        source = Path(module).read_text()
        for mutant in mutants(module):
            if mutant["line"] not in changed[module] or (mutated := mutate(source, mutant)) is None:
                continue
            jobs.append((module, mutated, sorted(on_line.get((module, mutant["line"]), everyone))))
            made.append({k: v for k, v in mutant.items() if k != "args"}
                        | {"mutated": first_difference(source, mutated)})  # fmt: skip
    counts = {"changed_lines": sum(map(len, changed.values())), "mutants": len(jobs)}
    outcomes = defaultdict(list)
    if jobs:  # with no node ids, the baseline would run the whole suite
        check_baseline(sorted({test for _, _, tests in jobs for test in tests}), pytest_args, timeout)
    for row, report in zip(made, fork_runs(jobs, [*pytest_args, "-x"], timeout, workers)):
        if report is TIMED_OUT:
            outcome = "timeouts"
        elif report is None or report.strays:
            outcome = "crashed"
        else:
            outcome = "killed" if report.failed else "survived"
        outcomes[outcome].append(row)
        log(f"{mutant_id(row)} {outcome}")
    return (
        counts
        | {kind: len(outcomes[kind]) for kind in ("killed", "survived", "timeouts", "crashed")}
        | {"survivors": outcomes["survived"]}
    )


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
    run.add_argument("--pytest-args", default="-q -p no:cacheprovider", help="add --no-cov under a coverage gate")
    run.add_argument("--timeout", type=float, default=300.0, help="seconds per mutant's test run")
    run.add_argument("--workers", type=int, default=os.cpu_count(), help="mutants run side by side")
    judge = sub.add_parser("verdict", help="keep, redundant, or kills-nothing for every test in a matrix")
    judge.add_argument("matrix")
    diff = sub.add_parser(
        "survivors",
        help="the mutants on lines changed since --base that no test notices; exits 1 when any survive or time out, "
        "2 on a failed baseline, 3 when changed lines made no mutant",
    )
    diff.add_argument("contexts")
    diff.add_argument("--base", required=True, help="the commit the branch started from")
    diff.add_argument("--paths", nargs="+", required=True, help="the source directories or files to mutate")
    for flag in ("--pytest-args", "--timeout", "--workers"):
        action = next(a for a in run._actions if flag in a.option_strings)
        diff.add_argument(flag, type=action.type, default=action.default, help=action.help)
    args = parser.parse_args(argv)

    if args.command == "candidates":
        result = candidates(json.loads(Path(args.contexts).read_text()))
    elif args.command == "survivors":
        try:
            result = survivors(
                json.loads(Path(args.contexts).read_text()),
                changed_lines(args.base, args.paths),
                shlex.split(args.pytest_args),
                args.timeout,
                args.workers,
                log=lambda line: print(line, file=sys.stderr, flush=True),
            )
        except BaselineError as error:
            print(f"thin: baseline failed: {error}", file=sys.stderr)
            return 2
        except subprocess.CalledProcessError as error:  # a bad --base must not read as "nothing changed"
            print(f"thin: git failed: {error.stderr.strip()}", file=sys.stderr)
            return 2
        print(json.dumps(result, indent=1))
        if result["changed_lines"] and not result["mutants"]:
            print(f"thin: {result['changed_lines']} changed lines made no mutant: comments only, or --paths "
                  "misses the changed code", file=sys.stderr)  # fmt: skip
            return 3
        return 1 if result["survived"] or result["timeouts"] else 0
    elif args.command == "matrix":
        only = json.loads(Path(args.only).read_text())["candidates"] if args.only else args.tests
        try:
            result = kill_matrix(
                json.loads(Path(args.contexts).read_text()),
                only,
                shlex.split(args.pytest_args),
                args.timeout,
                args.workers,
                log=lambda line: print(line, file=sys.stderr, flush=True),
            )
        except BaselineError as error:
            print(f"thin: baseline failed: {error}", file=sys.stderr)
            return 2
    else:
        result = verdict(json.loads(Path(args.matrix).read_text()))
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
