# ABOUTME: Finds redundant tests for compost:thin: per-test coverage narrows the candidates, a full kill matrix
# ABOUTME: (every failing test per mutant, not the first) proves which ones no mutant needs. `survivors` runs the
# ABOUTME: mutants on a branch's changed lines for compost:verify. Mutant runs need pytest and cosmic-ray.
import argparse
import ast
import functools
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
from decimal import Decimal
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


OWN = "thin/"  # the operators below, for breaks cosmic-ray never makes; `--operators stock` leaves them out
PREDICATE_CALLS = {"isinstance", "issubclass", "hasattr", "callable", "all", "any", "bool"}
PREDICATE_METHODS = {"startswith", "endswith", "exists", "isdigit", "isalpha", "isalnum", "isspace", "isupper",
                     "islower", "isidentifier", "isdisjoint", "issubset", "issuperset"}  # and any is_* or has_*  # fmt: skip
RETURN_CONSTANTS = {"bool": ["True", "False"], "str": ['""'], "list": ["[]"], "dict": ["{}"], "set": ["set()"],
                    "tuple": ["()"], "int": ["0"], "float": ["0.0"]}  # fmt: skip
SAME_TYPE_METHODS = {"strip", "lstrip", "rstrip", "removeprefix", "removesuffix", "lower", "upper", "casefold",
                     "replace", "expanduser", "resolve", "absolute"}  # fmt: skip
ORDERINGS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)
WRAPPERS = {"sorted", "fromkeys"}  # `sorted(xs)` and `dict.fromkeys(xs)` become `xs`


def predicate_shaped(value: ast.expr) -> bool:
    """Whether a returned expression reads as a yes or no, so its function gets True and False as constants."""
    if isinstance(value, (ast.Compare, ast.BoolOp)) or isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.Not):
        return True
    if isinstance(value, ast.Constant):
        return isinstance(value.value, bool)
    if isinstance(value, ast.Call):
        func = value.func
        if isinstance(func, ast.Name):
            return func.id in PREDICATE_CALLS
        return isinstance(func, ast.Attribute) and (
            func.attr in PREDICATE_METHODS or func.attr.startswith(("is_", "has_"))
        )
    return False


def kinds(annotation: ast.expr) -> list[str]:
    """The type names an annotation allows, lowercased: `Optional["List[str]"]` gives list and none."""
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):  # a forward reference
        return kinds(ast.parse(annotation.value, mode="eval").body)
    if isinstance(annotation, ast.BinOp):  # X | Y
        return kinds(annotation.left) + kinds(annotation.right)
    if isinstance(annotation, ast.Subscript):
        outer = kinds(annotation.value)
        inner = annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else [annotation.slice]
        if outer == ["optional"]:
            return [*kinds(inner[0]), "none"]
        return [kind for part in inner for kind in kinds(part)] if outer == ["union"] else outer
    name = annotation.attr if isinstance(annotation, ast.Attribute) else getattr(annotation, "id", "none")
    return [name.lower()]


def return_constants(function: ast.FunctionDef | ast.AsyncFunctionDef, value: ast.expr) -> list[str]:
    """The constants a `return value` in `function` is swapped for: by its annotation, else by the value's shape."""
    if function.returns is not None:
        found = [constant for kind in kinds(function.returns) for constant in RETURN_CONSTANTS.get(kind, ["None"])]
    else:
        found = ["True", "False"] if predicate_shaped(value) else ["None"]
    return [constant for constant in dict.fromkeys(found) if constant != ast.unparse(value)]


def nudged(literal: str) -> list[str]:
    """A float threshold one step either side, the step one digit finer than the literal: 0.7 gives 0.69 and 0.71."""
    value = Decimal(literal.replace("_", ""))
    step = Decimal(1).scaleb(value.as_tuple().exponent - 1)
    return [str(value - step), str(value + step)]


def breaks(tree: ast.Module, source: str, parents: dict[ast.AST, ast.AST]):
    """Yield (operator, node, text, expression) for each break of the module: put `text` where `node` is.

    An expression's text is parenthesized when it goes in; a statement's goes in as it is.
    """
    annotations = {
        id(part)
        for node in ast.walk(tree)
        for field in ("annotation", "returns")
        if isinstance(getattr(node, field, None), ast.expr)
        for part in ast.walk(getattr(node, field))
    }  # fmt: skip
    segment = functools.partial(ast.get_source_segment, source)
    for node in ast.walk(tree):
        parent = parents.get(node)
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            or (isinstance(node, ast.If) and not node.orelse and not segment(node).startswith("elif"))
        ):
            yield "thin/DeleteStatement", node, "pass", False
        elif isinstance(node, ast.Return) and node.value is not None:
            function = parent
            while not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
                function = parents[function]
            if not isinstance(function, ast.Module):
                for constant in return_constants(function, node.value):
                    yield "thin/ReturnConstant", node.value, constant, True
        elif isinstance(node, ast.BoolOp):
            joiner = " and " if isinstance(node.op, ast.And) else " or "
            for drop in range(len(node.values)):
                kept = [f"({segment(value)})" for index, value in enumerate(node.values) if index != drop]
                yield "thin/DropTerm", node, joiner.join(kept), True
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("all", "any"):
            [terms] = node.args if len(node.args) == 1 else [None]
            if isinstance(terms, (ast.List, ast.Tuple, ast.Set)) and len(terms.elts) > 1:
                for drop in range(len(terms.elts)):
                    kept = ", ".join(segment(elt) for index, elt in enumerate(terms.elts) if index != drop)
                    yield "thin/DropTerm", node, f"{node.func.id}([{kept}])", True
        elif isinstance(node, (ast.Constant, ast.JoinedStr)) and isinstance(getattr(node, "value", ""), str):
            # An f-string goes whole; its literal parts, docstrings, and annotations are left alone.
            if not isinstance(parent, (ast.Expr, ast.JoinedStr, ast.FormattedValue)) and id(node) not in annotations:
                other = (
                    "YY" if getattr(node, "value", None) == "XX" else "XX"
                )  # nothing of the original left for `in` or a regex to find
                yield "thin/ReplaceString", node, repr(other), True
        elif isinstance(node, ast.Constant) and type(node.value) is float:
            if isinstance(parent, ast.UnaryOp) and isinstance(parent.op, ast.USub):  # -0.5 is a unary minus on 0.5
                node, parent = parent, parents[parent]
            ordered = isinstance(parent, ast.Compare) and all(isinstance(op, ORDERINGS) for op in parent.ops)
            scope = parent
            while not isinstance(scope, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                scope = parents[scope]
            if ordered or isinstance(scope, ast.Module):  # compared here, or a module or class constant read later
                for text in nudged(segment(node)):
                    yield "thin/NudgeThreshold", node, text, True
        if isinstance(node, ast.Call) and not isinstance(parent, ast.Expr):  # a call statement is deleted instead
            name = getattr(node.func, "attr", getattr(node.func, "id", None))
            if isinstance(node.func, ast.Attribute) and name in SAME_TYPE_METHODS:
                yield "thin/DropCall", node, segment(node.func.value), True
            elif name in WRAPPERS and len(node.args) == 1:
                yield "thin/DropCall", node, segment(node.args[0]), True


def own_mutants(module: str) -> list[dict]:
    """The breaks cosmic-ray has no operator for (#124), each the span of `module` it replaces and its new text."""
    source = Path(module).read_text()
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    found, counts = [], defaultdict(int)
    for operator, node, text, expression in breaks(tree, source, parents):
        span = [node.lineno, node.col_offset, node.end_lineno, node.end_col_offset]
        statement = node
        while not isinstance(statement, ast.stmt):
            statement = parents[statement]
        # Coverage records a statement on its first line, so a break further down it goes by that line.
        found.append({"module": module, "operator": operator, "occurrence": counts[operator],
                      "line": statement.lineno, "args": {"span": span, "text": text, "expression": expression}})  # fmt: skip
        counts[operator] += 1
    return found


def splice(source: str, span: list[int], text: str, expression: bool) -> str | None:
    """`source` with `text` in place of the span, padded so no line moves; None when the result doesn't parse.

    ast's columns count UTF-8 bytes, so the splice works on bytes.
    """
    data = source.encode()
    starts = [0]
    for line in data.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    begin, end = starts[span[0] - 1] + span[1], starts[span[2] - 1] + span[3]
    pad = "\n" * max(0, data[begin:end].count(b"\n") - text.count("\n"))
    new = f"({text}{pad})" if expression else text + pad
    mutated = (data[:begin] + new.encode() + data[end:]).decode()
    try:
        ast.parse(mutated)
    except SyntaxError:
        return None
    return mutated


def mutants(module: str, own: bool = True) -> list[dict]:
    """Every mutation cosmic-ray would make in one module, and with `own` thin's own operators too, in line order."""
    from cosmic_ray.commands.init import _all_work_items  # private, but it is how cosmic-ray init lists mutants

    found = [
        {"module": module, "operator": m.operator_name, "args": m.operator_args, "occurrence": m.occurrence,
         "line": m.start_pos[0]}
        for item in _all_work_items([Path(module)], {})
        for m in item.mutations
    ]  # fmt: skip
    if own:
        found += own_mutants(module)
    return sorted(found, key=lambda m: (m["line"], m["operator"], m["occurrence"]))


def mutate(source: str, mutant: dict) -> str | None:
    """The mutated source, or None when the mutant can't be made (cosmic-ray's AST walk crashes on a few)."""
    if mutant["operator"].startswith(OWN):
        return splice(source, **mutant["args"])
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

    os.setsid()  # its own process group, so the parent can stop whatever the tests start along with it
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


def stop_group(pid: int) -> None:
    """Kill what is left of a child's process group: a mutant can leave a test's own subprocesses running."""
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def fork_runs(jobs: list[tuple], pytest_args: list[str], timeout: float, workers: int,
              progress=None) -> list[Report | TimedOut | None]:  # fmt: skip
    """Run each (module, source, tests) job in a child forked from this already-warm process, `workers` at a time.

    Forking skips the interpreter start and pytest import that dominate a short test run, and serving the mutant
    from memory leaves the tree untouched, so the children can run side by side. `progress(done, total)` is
    called as each job finishes.
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
                stop_group(pid)
                if not done:
                    os.waitpid(pid, 0)
                results[index] = read_report(report, tests) if done else TIMED_OUT
                del running[pid]
                if progress:
                    progress(len(results), len(jobs))
            time.sleep(0.005)
    return [results[index] for index in range(len(jobs))]


def check_baseline(tests: list[str], pytest_args: list[str], timeout: float | None) -> float:
    """Raise unless the unmutated tests all pass and the report names each one; return the timeout to run mutants by.

    Under a broken setup every run fails, and every mutant would read as killed. With no timeout given, a mutant
    gets ten times what the baseline took, and never less than 30 seconds.
    """
    started = time.monotonic()
    [baseline] = fork_runs([(None, None, tests)], pytest_args, timeout or 3600, 1)
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
    return timeout or max(30.0, 10 * (time.monotonic() - started))


def kill_matrix(contexts: dict, only: list[str] | None, pytest_args: list[str], timeout: float | None,
                workers: int, log=print, own: bool = True) -> dict:  # fmt: skip
    """Run each mutant on a line the selected tests cover against every test covering that line; record each killer.

    Only the selected tests are mutated over every line they run, so only they can be judged from the result. The
    tests must pass unmutated first: under a broken setup every run fails, every test kills every mutant, and the
    verdict would call all but one of them redundant. With no `timeout`, a mutant's run gets ten times the
    baseline's wall time, at least 30 seconds: a mutant that hangs costs that, not a fixed five minutes.
    """
    lines = covered_lines(contexts)
    imported = {(path, int(line)) for path, info in contexts["files"].items()
                for line, names in info["contexts"].items() if "" in names}  # fmt: skip
    selected = set(only) if only is not None else set(lines)
    on_line = defaultdict(set)
    for name, pairs in lines.items():
        for pair in pairs:
            on_line[pair].add(name)
    wanted = {pair for name in selected & set(lines) for pair in lines[name]}
    everyone = sorted({test for pair in wanted for test in on_line[pair]})
    if not everyone:  # with no node ids, pytest would run the whole suite
        return {"selected": sorted(selected & set(lines)), "mutants": []}
    timeout = check_baseline(everyone, pytest_args, timeout)
    jobs, made = [], []
    for module in sorted({path for path, _ in wanted}):
        source = Path(module).read_text()
        in_module = sorted({test for path, line in wanted if path == module for test in on_line[(path, line)]})
        for mutant in mutants(module, own):
            # A threshold set at import, `FOUND = 0.7`, runs under no test: try it on the module's selected tests.
            place = (module, mutant["line"])
            at_import = mutant["operator"] == "thin/NudgeThreshold" and place in imported and place not in on_line
            if (module, mutant["line"]) not in wanted and not at_import:
                continue
            mutated = mutate(source, mutant)
            if mutated is None:
                continue
            covering = in_module if at_import else sorted(on_line[(module, mutant["line"])])
            jobs.append((module, mutated, covering))
            made.append({k: v for k, v in mutant.items() if k != "args"}
                        | {"mutated": first_difference(source, mutated), "covering": covering})  # fmt: skip
    rows = []

    def progress(done: int, total: int) -> None:
        if done % 100 == 0 or done == total:
            log(f"{done}/{total} mutants run")

    for row, report in zip(made, fork_runs(jobs, pytest_args, timeout, workers, progress)):
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


def survivors(contexts: dict, changed: dict[str, set[int]], pytest_args: list[str], timeout: float | None, workers: int,
              log=print, own: bool = False) -> dict:  # fmt: skip
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
        for mutant in mutants(module, own):
            if mutant["line"] not in changed[module] or (mutated := mutate(source, mutant)) is None:
                continue
            jobs.append((module, mutated, sorted(on_line.get((module, mutant["line"]), everyone))))
            made.append({k: v for k, v in mutant.items() if k != "args"}
                        | {"mutated": first_difference(source, mutated)})  # fmt: skip
    counts = {"changed_lines": sum(map(len, changed.values())), "mutants": len(jobs)}
    outcomes = defaultdict(list)
    if jobs:  # with no node ids, the baseline would run the whole suite
        timeout = check_baseline(sorted({test for _, _, tests in jobs for test in tests}), pytest_args, timeout)
    for row, report in zip(made, fork_runs(jobs, [*pytest_args, "-x"], timeout, workers)):
        if report is TIMED_OUT:
            outcome = "timeouts"
        elif report is None or report.strays:
            outcome = "crashed"
        else:
            outcome = "killed" if report.failed else "survived_strings" if is_string(row) else "survived"
        outcomes[outcome].append(row)
        log(f"{mutant_id(row)} {outcome}")
    return (
        counts
        | {kind: len(outcomes[kind]) for kind in ("killed", "survived", "timeouts", "crashed")}
        | {"survivors": outcomes["survived"], "survived_strings": outcomes["survived_strings"]}
    )


def is_string(row: dict) -> bool:
    """A changed string survives most often as an equivalent mutant (a message nobody reads), so it is listed apart."""
    return row["operator"] == "thin/ReplaceString"


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
    survived = {False: [], True: []}
    for row in sorted(rows, key=mutant_id):
        if not row["killers"]:
            survived[is_string(row)].append(mutant_id(row))
    return {"mutants": len(rows), "survived": survived[False], "survived_strings": survived[True],
            "minimal": sorted(keep & selected), "tests": tests}  # fmt: skip


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
    run.add_argument("--timeout", type=float, help="seconds per mutant's test run; default 10x the baseline's")
    run.add_argument("--workers", type=int, default=os.cpu_count(), help="mutants run side by side")
    run.add_argument("--operators", choices=["all", "stock"], default="all",
                     help="stock: cosmic-ray's only, without thin's own (thin/...), to compare with a stock run")  # fmt: skip
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
    diff.add_argument("--operators", choices=["all", "stock"], default="stock", help="all: add thin's own operators")
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
                own=args.operators == "all",
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
                own=args.operators == "all",
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
