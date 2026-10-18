# ABOUTME: Tests thin.py: coverage candidates from per-test contexts, the kill matrix run by real cosmic-ray and real
# ABOUTME: pytest in forked children on a toy project, the baseline guard, and the keep / redundant / kills-nothing verdict.
import json
import os
import sys
import textwrap
import time
from pathlib import Path

import pytest
import thin
from conftest import commit, run_git

PYTEST = ["-q", "-p", "no:cacheprovider"]


def contexts(files: dict[str, dict[int, list[str]]]) -> dict:
    """A `coverage json --show-contexts` report: file -> line -> the contexts that ran it."""
    return {
        "files": {path: {"contexts": {str(n): names for n, names in lines.items()}} for path, lines in files.items()}
    }


TOY_TESTS = ["test_age.py::test_boundary", "test_age.py::test_grown_up", "test_age.py::test_runs_only"]


def NO_LOG(line: str) -> None:
    pass


def make_toy(tmp_path):
    """age.py with three tests: one pins both sides of the boundary, one restates half of it, one asserts nothing."""
    (tmp_path / "age.py").write_text("def adult(age):\n    return age >= 18\n")
    (tmp_path / "test_age.py").write_text(
        textwrap.dedent("""\
            from age import adult

            def test_boundary():
                assert adult(18) and adult(30) and not adult(17)

            def test_grown_up():
                assert adult(18)

            def test_runs_only():
                adult(5)
            """)
    )
    return contexts({"age.py": {1: [""], 2: [f"{t}|run" for t in TOY_TESTS]}})


@pytest.fixture
def toy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return make_toy(tmp_path)


@pytest.fixture(scope="module")
def toy_matrix(tmp_path_factory):
    """The toy's full kill matrix, run once and shared by the tests that read it."""
    root = tmp_path_factory.mktemp("toy")
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(root)
        report = make_toy(root)
        return root, thin.kill_matrix(report, None, PYTEST, 60, 2, log=NO_LOG)


def test_candidates_are_tests_whose_lines_equal_or_sit_inside_anothers():
    report = contexts(
        {
            "m.py": {
                1: [""],
                2: ["t.py::a|run", "t.py::b|run", "t.py::c|run", "t.py::d|setup"],
                3: ["t.py::c|run"],
                4: ["t.py::d|run"],
            }
        }
    )
    found = thin.candidates(report)
    assert found["tests"] == 4
    assert found["same_lines"] == [["t.py::a", "t.py::b"]]
    assert found["inside"] == {"t.py::a": "t.py::c", "t.py::b": "t.py::c"}
    assert found["candidates"] == ["t.py::a", "t.py::b"]
    assert found["cover_keeps"] == 2


def test_greedy_cover_skips_what_is_already_covered():
    sets = {"a": {1, 2}, "b": {2, 3}, "c": {3}}
    assert thin.greedy_cover(sets) == ["a", "b"]
    assert thin.greedy_cover(sets, frozenset({1, 2})) == ["b"]
    assert thin.greedy_cover({}) == []


@pytest.mark.parametrize(
    ("node_id", "key"),
    [
        ("tests/test_x.py::test_y[a b]", ("tests.test_x", "test_y[a b]")),
        ("t.py::TestC::test_y", ("t.TestC", "test_y")),
        ("t.py::test_route[a::b]", ("t", "test_route[a::b]")),
    ],
    ids=["function", "class", "parameter holding ::"],
)
def test_junit_key_matches_what_pytest_writes(node_id, key):
    assert thin.junit_key(node_id) == key


def test_read_report_keeps_failures_it_cannot_match_instead_of_dropping_them(tmp_path):
    report = tmp_path / "junit.xml"
    report.write_text(
        "<testsuites><testsuite>"
        '<testcase classname="t" name="a"><failure/></testcase>'
        '<testcase classname="t" name="b"><error/></testcase>'
        '<testcase classname="t" name="c"/>'
        '<testcase classname="t" name="passing stranger"/>'
        '<testcase classname="" name="t"><error/></testcase>'
        "</testsuite></testsuites>"
    )
    found = thin.read_report(report, ["t.py::a", "t.py::b", "t.py::c", "t.py::d"])
    assert found.named == {"t.py::a", "t.py::b", "t.py::c"}
    assert found.failed == {"t.py::a", "t.py::b"}
    assert found.strays == ["::t"]
    assert thin.read_report(tmp_path / "missing.xml", ["t.py::a"]) is None


def test_mutated_source_serves_the_mutant_and_leaves_other_imports_alone(tmp_path, monkeypatch):
    (tmp_path / "toy_served.py").write_text("VALUE = 1\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    finder = thin.MutatedSource(str(tmp_path / "toy_served.py"), "VALUE = 2\n")
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])
    monkeypatch.delitem(sys.modules, "toy_served", raising=False)
    import toy_served

    assert toy_served.VALUE == 2
    assert (tmp_path / "toy_served.py").read_text() == "VALUE = 1\n"
    assert finder.find_spec("json") is None
    assert finder.find_spec("no_such_module_anywhere") is None
    monkeypatch.delitem(sys.modules, "toy_served")


def test_mutate_makes_the_mutant_in_memory_or_none_when_cosmic_ray_cannot(tmp_path, monkeypatch):
    (tmp_path / "cmp.py").write_text("x = a >= b\n")
    [eq] = [m for m in thin.mutants(str(tmp_path / "cmp.py")) if m["operator"].endswith("GtE_Eq")]
    assert thin.mutate("x = a >= b\n", eq) == "x = a == b\n"

    def crash(*args):
        raise AttributeError("'PythonNode' object has no attribute 'value'")

    monkeypatch.setattr("cosmic_ray.mutating.mutate_code", crash)
    assert thin.mutate("x = a >= b\n", eq) is None


@pytest.mark.parametrize(
    ("source", "operator", "expected"),
    [
        ("def f(x):\n    if x < 0:\n        raise ValueError(x)\n    return x\n", "DeleteStatement",
         ["def f(x):\n    pass\n\n    return x\n"]),
        ('def f(p):\n    """Doc."""\n    p.mkdir()\n', "DeleteStatement", ['def f(p):\n    """Doc."""\n    pass\n']),
        ("if a:\n    pass\nelif b:\n    pass\n", "DeleteStatement", []),
        ("def f(x) -> bool:\n    return x.ok\n", "ReturnConstant",
         ["def f(x) -> bool:\n    return (True)\n", "def f(x) -> bool:\n    return (False)\n"]),
        ("def f(x) -> list[str] | None:\n    return x\n", "ReturnConstant",
         ["def f(x) -> list[str] | None:\n    return ([])\n", "def f(x) -> list[str] | None:\n    return (None)\n"]),
        ("def f(x) -> Optional['bool']:\n    return x\n", "ReturnConstant",
         ["def f(x) -> Optional['bool']:\n    return (True)\n", "def f(x) -> Optional['bool']:\n    return (False)\n",
          "def f(x) -> Optional['bool']:\n    return (None)\n"]),
        ("def f(x) -> t.Union[t.List[int], None]:\n    return x\n", "ReturnConstant",
         ["def f(x) -> t.Union[t.List[int], None]:\n    return ([])\n",
          "def f(x) -> t.Union[t.List[int], None]:\n    return (None)\n"]),
        ("def f(x):\n    return x.is_file()\n", "ReturnConstant",
         ["def f(x):\n    return (True)\n", "def f(x):\n    return (False)\n"]),
        ("def f(x):\n    return x + 1\n", "ReturnConstant", ["def f(x):\n    return (None)\n"]),
        ("def f(d):\n    return d.isoformat()\n", "ReturnConstant", ["def f(d):\n    return (None)\n"]),
        ("def f(x):\n    if x:\n        return isinstance(x, int)\n", "ReturnConstant",
         ["def f(x):\n    if x:\n        return (True)\n", "def f(x):\n    if x:\n        return (False)\n"]),
        ("def f():\n    return False\n", "ReturnConstant", ["def f():\n    return (True)\n"]),
        ("ok = a and (b or c)\n", "DropTerm",
         ["ok = ((b or c))\n", "ok = ((a))\n", "ok = a and (((c)))\n", "ok = a and (((b)))\n"]),
        ("ok = all((a, b, c))\n", "DropTerm", ["ok = (all([b, c]))\n", "ok = (all([a, c]))\n", "ok = (all([a, b]))\n"]),
        ("ok = any([a])\n", "DropTerm", []),
        ("if (a and\n        b):\n    pass\n", "DropTerm", ["if (((b)\n)):\n    pass\n", "if (((a)\n)):\n    pass\n"]),
        ('def f(x: "Path"):\n    """Doc."""\n    return {"k": ""}[f"{x}-"]\n', "ReplaceString",
         ['def f(x: "Path"):\n    """Doc."""\n    return {(\'XX\'): ""}[f"{x}-"]\n',
          'def f(x: "Path"):\n    """Doc."""\n    return {"k": (\'XX\')}[f"{x}-"]\n',
          'def f(x: "Path"):\n    """Doc."""\n    return {"k": ""}[(\'XX\')]\n']),
        ("def f(s):\n    return s >= 0.7 and s < 1e-3 and s == 0.5 and s > 18\n", "NudgeThreshold",
         ["def f(s):\n    return s >= (0.69) and s < 1e-3 and s == 0.5 and s > 18\n",
          "def f(s):\n    return s >= (0.71) and s < 1e-3 and s == 0.5 and s > 18\n",
          "def f(s):\n    return s >= 0.7 and s < (0.0009) and s == 0.5 and s > 18\n",
          "def f(s):\n    return s >= 0.7 and s < (0.0011) and s == 0.5 and s > 18\n"]),
        ("def f(s):\n    return s > -0.5\n", "NudgeThreshold",
         ["def f(s):\n    return s > (-0.49)\n", "def f(s):\n    return s > (-0.51)\n"]),
        ("FOUND = {'a': 0.75}\ndef f(): sleep(0.5)\n", "NudgeThreshold",
         ["FOUND = {'a': (0.749)}\ndef f(): sleep(0.5)\n", "FOUND = {'a': (0.751)}\ndef f(): sleep(0.5)\n"]),
        ("a = p.removeprefix('x').upper\nb = list(dict.fromkeys(ys))\nc = sorted(ys, key=len)\n"
         "p.strip()\nsorted(ys)\n", "DropCall",
         ["a = (p).upper\nb = list(dict.fromkeys(ys))\nc = sorted(ys, key=len)\np.strip()\nsorted(ys)\n",
          "a = p.removeprefix('x').upper\nb = list((ys))\nc = sorted(ys, key=len)\np.strip()\nsorted(ys)\n",
          "a = p.removeprefix('x').upper\nb = list(dict.fromkeys(ys))\nc = (ys)\np.strip()\nsorted(ys)\n"]),
    ],
    ids=["guard", "call statement, not docstring", "no elif", "bool annotation", "first of a union", "optional forward reference",
         "typing union",
         "predicate method", "no annotation", "is-prefix not a predicate",
         "predicate call in a branch", "only the other bool", "one per term",
         "all() terms", "one term left", "lines kept", "strings and whole f-strings, not docstrings or annotations", "ordered float comparisons", "negative threshold",
         "module constants", "same-type methods and wrappers"],
)  # fmt: skip
def test_thin_operators_make_the_breaks_cosmic_ray_cannot(tmp_path, source, operator, expected):
    (tmp_path / "m.py").write_text(source)
    made = [m for m in thin.own_mutants(str(tmp_path / "m.py")) if m["operator"] == f"thin/{operator}"]
    mutated = [thin.mutate(source, m) for m in made]
    assert sorted(mutated) == sorted(expected)
    assert [m["occurrence"] for m in made] == list(range(len(made)))
    assert all(text.count("\n") == source.count("\n") for text in mutated)


def test_a_thin_mutant_that_would_not_parse_is_left_out():
    span = {"span": [1, 0, 2, 2], "text": "pass", "expression": False}
    assert thin.mutate("f(\n1); g()\n", {"operator": "thin/DeleteStatement", "args": span}) is None
    assert thin.mutate(
        "é = f(\n1)\n",
        {"operator": "thin/DropCall", "args": span | {"span": [1, 5, 2, 2], "text": "x", "expression": True}},
    ) == ("é = (x\n)\n")


GUARDS = """\
def parse(age):
    if age < 0:
        raise ValueError("negative")
    return age


def is_test(name: str) -> bool:
    return name.startswith("test_")


def ready(a, b):
    return a and b


def passes(score):
    return score >= PASS


PASS = 0.7


def unused(score):
    return score > 0.5
"""

GUARDS_TESTS = {
    "test_parses": "assert parse(3) == 3",
    "test_rejects_negative": "with pytest.raises(ValueError, match='negative'):\n        parse(-1)",
    "test_is_test": "assert is_test('test_x')",
    "test_is_not_test": "assert not is_test('x')",
    "test_ready": "assert ready(True, True) and not ready(True, False) and not ready(False, True)",
    "test_at_threshold": "assert passes(0.7)",
    "test_just_under": "assert not passes(0.69)",
}


@pytest.fixture(scope="module")
def guards_matrix(tmp_path_factory):
    """A kill matrix over guards.py, whose tests each pin one break that only thin's own operators make."""
    root = tmp_path_factory.mktemp("guards")
    (root / "guards.py").write_text(GUARDS)
    (root / "test_guards.py").write_text(
        "import pytest\nfrom guards import *\n"
        + "".join(f"\ndef {name}():\n    {body}\n" for name, body in GUARDS_TESTS.items())
    )
    ids = {name: f"test_guards.py::{name}" for name in GUARDS_TESTS}
    runs = {2: ["test_parses", "test_rejects_negative"], 3: ["test_rejects_negative"], 4: ["test_parses"],
            8: ["test_is_test", "test_is_not_test"], 12: ["test_ready"], 16: ["test_at_threshold", "test_just_under"]}  # fmt: skip
    imported = {1: [""], 19: [""], 22: [""]}
    report = contexts({"guards.py": imported | {n: [f"{ids[t]}|run" for t in ts] for n, ts in runs.items()}})
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(root)
        return thin.kill_matrix(report, None, PYTEST, 60, 4, log=NO_LOG)


@pytest.mark.parametrize(
    ("line", "mutated", "killers"),
    [
        (2, "pass", ["test_rejects_negative"]),
        (8, "return (True)", ["test_is_not_test"]),
        (12, "return ((b))", ["test_ready"]),
        (12, "return ((a))", ["test_ready"]),
        (3, "raise ValueError(('XX'))", ["test_rejects_negative"]),
        (19, "PASS = (0.69)", ["test_just_under"]),
        (19, "PASS = (0.71)", ["test_at_threshold"]),
    ],
    ids=["AC-1 deleted guard", "AC-2 constant return", "AC-3 first term dropped", "AC-3 second term dropped",
         "AC-4 changed message", "AC-5 threshold under", "AC-5 threshold over"],
)  # fmt: skip
def test_the_matrix_makes_the_breaks_that_only_one_test_catches(guards_matrix, line, mutated, killers):
    [row] = [row for row in guards_matrix["mutants"] if row["line"] == line and row["mutated"] == mutated]
    assert row["operator"].startswith(thin.OWN)
    assert row["killers"] == [f"test_guards.py::{name}" for name in killers]


def test_the_matrix_tries_a_threshold_set_at_import_on_every_test_of_its_module(guards_matrix):
    rows = [row for row in guards_matrix["mutants"] if row["line"] == 19]
    assert {row["operator"] for row in rows} == {"thin/NudgeThreshold"}
    assert all(row["covering"] == sorted(f"test_guards.py::{name}" for name in GUARDS_TESTS) for row in rows)
    assert not [row for row in guards_matrix["mutants"] if row["line"] == 23]  # a compare no test runs is no gap


def test_a_break_inside_a_statement_goes_by_the_line_coverage_records(tmp_path):
    (tmp_path / "m.py").write_text('def f():\n    raise ValueError(\n        "negative"\n    )\n')
    [string] = [m for m in thin.own_mutants(str(tmp_path / "m.py")) if m["operator"] == "thin/ReplaceString"]
    assert string["line"] == 2 and string["args"]["span"][0] == 3


def test_stock_operators_leave_thin_out(tmp_path):
    (tmp_path / "guards.py").write_text(GUARDS)
    operators = {m["operator"] for m in thin.mutants(str(tmp_path / "guards.py"), own=False)}
    assert operators and not any(op.startswith(thin.OWN) for op in operators)
    assert {m["operator"] for m in thin.mutants(str(tmp_path / "guards.py"))} > operators


def test_the_kill_matrix_runs_every_covering_test_without_touching_the_file(toy_matrix):
    root, matrix = toy_matrix
    assert (root / "age.py").read_text() == "def adult(age):\n    return age >= 18\n"
    assert matrix["selected"] == TOY_TESTS
    rows = {(row["operator"], row["occurrence"]): row for row in matrix["mutants"]}
    eq = rows[("core/ReplaceComparisonOperator_GtE_Eq", 0)]
    assert eq["covering"] == TOY_TESTS
    assert eq["killers"] == ["test_age.py::test_boundary"]
    assert not any("test_age.py::test_runs_only" in row["killers"] for row in matrix["mutants"])


def test_the_verdict_keeps_the_boundary_and_flags_the_restatement_and_the_no_op(toy_matrix):
    result = thin.verdict(toy_matrix[1])
    assert result["minimal"] == ["test_age.py::test_boundary"]
    tests = result["tests"]
    assert tests["test_age.py::test_boundary"]["verdict"] == "keep"
    assert tests["test_age.py::test_boundary"]["unique"]
    assert tests["test_age.py::test_grown_up"]["verdict"] == "redundant"
    assert tests["test_age.py::test_grown_up"]["subsumed_by"] == "test_age.py::test_boundary"
    assert tests["test_age.py::test_runs_only"] == {"verdict": "kills-nothing", "kills": 0}


GT_ROW = {"module": "age.py", "operator": "gt", "occurrence": 0, "line": 2, "mutated": "return age > 18",
          "covering": TOY_TESTS}  # fmt: skip


def one_mutant(monkeypatch, line: int = 2, mutated: str | None = "def adult(age):\n    return age > 18\n"):
    """Swap cosmic-ray's mutant list for a single `>=` to `>` on `line`, made as `mutated`."""
    mutant = {"module": "age.py", "operator": "gt", "args": {}, "occurrence": 0, "line": line}
    monkeypatch.setattr(thin, "mutants", lambda module, own: [mutant])
    monkeypatch.setattr(thin, "mutate", lambda source, m: mutated)


def test_only_limits_mutation_to_the_selected_tests_lines(toy, monkeypatch):
    toy["files"]["other.py"] = {"contexts": {"1": ["test_age.py::test_elsewhere|run"]}}
    only = ["test_age.py::test_grown_up"]
    one_mutant(monkeypatch)
    assert thin.kill_matrix(toy, only, PYTEST, 60, 2, log=NO_LOG) == {
        "selected": only,
        "mutants": [GT_ROW | {"killers": ["test_age.py::test_boundary", "test_age.py::test_grown_up"]}],
    }
    one_mutant(monkeypatch, line=1)
    assert thin.kill_matrix(toy, only, PYTEST, 60, 2, log=NO_LOG)["mutants"] == []


class Died(Exception):
    """A matrix run that stops partway, as one does when its container restarts."""


def test_ac1_a_killed_matrix_resumes_with_only_the_remaining_mutants(toy, tmp_path, toy_matrix, monkeypatch):
    journal = tmp_path / "matrix.jsonl"
    finished = []

    def dies_after_two(line: str) -> None:
        if "killed by" in line:
            finished.append(line)
            if len(finished) == 2:
                raise Died

    with pytest.raises(Died):
        thin.kill_matrix(toy, None, PYTEST, 60, 1, log=dies_after_two, journal=journal)
    assert len(journal.read_text().splitlines()) == 2  # each row lands as its run ends, not when the matrix does
    with journal.open("a") as torn:  # a death mid-write leaves half a row
        torn.write('{"module": "age.py", "oper')
    runs = []
    fork_runs = thin.fork_runs
    monkeypatch.setattr(thin, "fork_runs", lambda jobs, *args: runs.append(len(jobs)) or fork_runs(jobs, *args))
    uninterrupted = toy_matrix[1]
    resumed = thin.kill_matrix(toy, None, PYTEST, 60, 2, log=NO_LOG, journal=journal, resume=thin.read_journal(journal))
    assert resumed == uninterrupted
    assert runs == [1, len(uninterrupted["mutants"]) - 2]  # the baseline, then only the mutants not yet run
    by_id = sorted(thin.read_journal(journal), key=thin.mutant_id)
    assert by_id == sorted(uninterrupted["mutants"], key=thin.mutant_id)


@pytest.mark.parametrize(
    "stale",
    [GT_ROW | {"operator": "gone"}, GT_ROW | {"mutated": "return age < 18"}, GT_ROW | {"covering": TOY_TESTS[:1]}],
    ids=["AC-2 id no longer listed", "same id, another mutant", "same mutant, other covering tests"],
)
def test_ac2_a_resumed_row_the_source_no_longer_makes_is_dropped_and_rerun(toy, tmp_path, monkeypatch, stale):
    one_mutant(monkeypatch)
    journal = tmp_path / "matrix.jsonl"
    matrix = thin.kill_matrix(toy, None, PYTEST, 60, 2, log=NO_LOG, journal=journal, resume=[stale | {"killers": []}])
    ran = GT_ROW | {"killers": ["test_age.py::test_boundary", "test_age.py::test_grown_up"]}
    assert matrix["mutants"] == [ran]
    assert thin.read_journal(journal) == [ran]


def test_a_mutant_cosmic_ray_cannot_make_is_left_out(toy, monkeypatch):
    one_mutant(monkeypatch, mutated=None)
    assert thin.kill_matrix(toy, None, PYTEST, 60, 2, log=NO_LOG)["mutants"] == []


@pytest.mark.parametrize(
    "mutated", ["import os\nos._exit(3)\n", "raise ImportError('boom')\n"], ids=["no report", "collection error"]
)
def test_a_mutant_that_breaks_the_run_counts_as_killed_by_every_covering_test(toy, monkeypatch, mutated):
    one_mutant(monkeypatch, mutated=mutated)
    [row] = thin.kill_matrix(toy, None, PYTEST, 60, 2, log=NO_LOG)["mutants"]
    assert row["crashed"] and row["killers"] == row["covering"] == TOY_TESTS


def test_an_empty_selection_runs_nothing(toy, monkeypatch):
    monkeypatch.setattr(thin, "fork_runs", lambda *args: pytest.fail("with no node ids pytest runs the whole suite"))
    assert thin.kill_matrix(toy, ["test_age.py::test_not_in_contexts"], PYTEST, 60, 2, log=NO_LOG) == {
        "selected": [],
        "mutants": [],
    }


def test_a_run_past_its_timeout_is_killed_and_reported_as_timed_out_not_crashed(toy, tmp_path):
    (tmp_path / "test_slow.py").write_text("import time\ndef test_slow():\n    time.sleep(30)\n")
    assert thin.fork_runs([(None, None, ["test_slow.py::test_slow"])], PYTEST, 1, 1) == [thin.TIMED_OUT]


def gone(pid: int) -> bool:
    """True once a process has exited: absent, or a zombie waiting for a reaper this container may not run."""
    try:
        return Path(f"/proc/{pid}/stat").read_text().split(") ")[1][0] == "Z"
    except FileNotFoundError:
        return True


SLEEP = "subprocess.Popen(['sleep', '60'], start_new_session={})"
NESTED = "import pathlib, subprocess, time; pathlib.Path('spawned.pid').write_text(str({}.pid)); time.sleep(60)"


@pytest.mark.parametrize(("then", "timeout"), [("pass", 20), ("time.sleep(30)", 2)], ids=["exits", "times out"])
@pytest.mark.parametrize(
    "spawn",
    [SLEEP.format(False), SLEEP.format(True), f"subprocess.Popen([sys.executable, '-c', {NESTED.format(SLEEP.format(True))!r}], start_new_session=True)"],
    ids=["in its group", "in a session of its own", "a session inside a session"],
)  # fmt: skip
def test_what_a_test_starts_dies_with_its_run(toy, tmp_path, then, timeout, spawn):
    # A session of its own is how a nested run's child escapes: thin.py's own tests fork runs, and so do its mutants.
    (tmp_path / "test_spawn.py").write_text(
        "import pathlib, subprocess, sys, time\n"
        "def test_spawn():\n"
        f"    child = {spawn}\n"
        "    if child.args[0] == 'sleep':\n"
        "        pathlib.Path('spawned.pid').write_text(str(child.pid))\n"
        "    while not pathlib.Path('spawned.pid').exists():\n"
        "        time.sleep(0.01)\n"
        f"    {then}\n"
    )
    thin.fork_runs([(None, None, ["test_spawn.py::test_spawn"])], PYTEST, timeout, 1)
    pid = int((tmp_path / "spawned.pid").read_text())
    deadline = time.monotonic() + 5
    while not gone(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert gone(pid)


def test_orphans_are_left_to_init_where_the_platform_cannot_adopt_them(monkeypatch):
    monkeypatch.setattr(thin.ctypes, "CDLL", lambda *args, **kwargs: object())  # a libc without prctl, as on macOS
    assert thin.adopt_orphans(True) is False
    assert thin.parent_of(os.getpid()) == os.getppid()
    gone_pid = os.fork()
    if gone_pid == 0:
        os._exit(0)
    os.waitpid(gone_pid, 0)
    assert thin.parent_of(gone_pid) is None


def test_children_read_stdin_from_devnull_so_a_read_cannot_block(toy, tmp_path):
    (tmp_path / "test_stdin.py").write_text("import os\ndef test_reads():\n    assert os.read(0, 1) == b''\n")
    # An open pipe on stdin blocks a read, as a terminal does; -s keeps pytest's capture from hiding it.
    read_end, write_end = os.pipe()
    saved = os.dup(0)
    os.dup2(read_end, 0)
    try:
        [report] = thin.fork_runs([(None, None, ["test_stdin.py::test_reads"])], [*PYTEST, "-s"], 5, 1)
    finally:
        os.dup2(saved, 0)
        for fd in (saved, read_end, write_end):
            os.close(fd)
    assert report is not None and report.named == {"test_stdin.py::test_reads"} and report.failed == set()


def test_children_drop_compost_scripts_from_sys_path_so_its_modules_cannot_shadow_the_projects(toy, tmp_path):
    kept = [p for p in sys.path if Path(p or ".").resolve() != thin.SCRIPTS]
    (tmp_path / "test_path.py").write_text(
        f"import sys\nfrom pathlib import Path\ndef test_path():\n"
        f"    assert {str(thin.SCRIPTS)!r} not in [str(Path(p or '.').resolve()) for p in sys.path]\n"
        f"    assert set({kept!r}) <= set(sys.path)\n"
    )
    [report] = thin.fork_runs([(None, None, ["test_path.py::test_path"])], PYTEST, 20, 1)
    assert report.named == {"test_path.py::test_path"} and report.failed == set()


@pytest.mark.parametrize(
    ("pytest_args", "test_body", "message"),
    [
        (PYTEST, "assert not adult(18)", "1 tests fail unmutated, e.g. test_age.py::test_grown_up"),
        ([*PYTEST, "--junitprefix=pkg"], "assert adult(18)", "never names test_age.py::test_boundary"),
        (PYTEST, "assert adult(18)\nthis is not python", "names a failure no selected test matches: ::test_age"),
    ],
    ids=["red baseline", "junit prefix", "collection error"],
)
@pytest.mark.parametrize(
    "run",
    [
        lambda toy, args: thin.kill_matrix(toy, None, args, 60, 2, log=NO_LOG),
        lambda toy, args: thin.survivors(toy, {"age.py": {2}}, args, 60, 2, log=NO_LOG),
        lambda toy, args: thin.kill_matrix(
            toy, None, args, 60, 2, log=NO_LOG, journal=Path("matrix.jsonl"), resume=[GT_ROW | {"killers": []}]
        ),
    ],
    ids=["matrix", "survivors", "matrix resumed"],
)
def test_mutation_refuses_to_run_on_a_baseline_that_is_not_green(toy, tmp_path, pytest_args, test_body, message, run):
    source = (tmp_path / "test_age.py").read_text().replace("assert adult(18)\n", f"{test_body}\n")
    (tmp_path / "test_age.py").write_text(source)
    (tmp_path / "matrix.jsonl").write_text("the rows so far\n")
    with pytest.raises(thin.BaselineError, match=message):
        run(toy, pytest_args)
    assert (tmp_path / "matrix.jsonl").read_text() == "the rows so far\n"  # kept for a resume once the code is fixed


def test_main_runs_each_stage_and_prints_json(toy, tmp_path, capsys, monkeypatch):
    one_mutant(monkeypatch)
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    assert thin.main(["candidates", "ctx.json"]) == 0
    found = json.loads(capsys.readouterr().out)
    assert found["candidates"] == TOY_TESTS
    (tmp_path / "cands.json").write_text(json.dumps(found))
    matrix = ["matrix", "ctx.json", "--only", "cands.json", "--pytest-args", " ".join(PYTEST)]
    assert thin.main(matrix) == 0
    out = capsys.readouterr()
    assert "age.py:2 gt#0 killed by 2/3" in out.err
    assert "1/1 mutants run" in out.err
    assert thin.read_journal(tmp_path / "matrix.jsonl") == json.loads(out.out)["mutants"]  # beside the contexts
    assert thin.main([*matrix, "--resume", "matrix.jsonl"]) == 0
    resumed = capsys.readouterr()
    assert resumed.out == out.out
    assert "1 of 1 journaled rows resumed" in resumed.err and "killed by" not in resumed.err
    (tmp_path / "matrix.json").write_text(out.out)
    assert thin.main(["verdict", "matrix.json"]) == 0
    assert json.loads(capsys.readouterr().out)["minimal"] == ["test_age.py::test_boundary"]


def test_main_matrix_takes_node_ids_in_place_of_a_candidates_file(toy, tmp_path, capsys, monkeypatch):
    one_mutant(monkeypatch)
    asked = []
    listed = thin.mutants
    monkeypatch.setattr(thin, "mutants", lambda module, own: asked.append(own) or listed(module, own))
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    args = ["matrix", "ctx.json", "--tests", "test_age.py::test_runs_only", "--workers", "1"]
    assert thin.main([*args, "--pytest-args", " ".join(PYTEST)]) == 0
    assert json.loads(capsys.readouterr().out)["selected"] == ["test_age.py::test_runs_only"]
    assert thin.main([*args, "--pytest-args", " ".join(PYTEST), "--operators", "stock"]) == 0
    assert asked == [True, False]


def test_main_exits_2_and_says_why_when_the_baseline_fails(toy, tmp_path, capsys):
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    assert thin.main(["matrix", "ctx.json", "--pytest-args=--no-such-option"]) == 2
    assert "thin: baseline failed: the unmutated tests left no report" in capsys.readouterr().err


def test_the_verdict_never_judges_a_test_outside_the_selection():
    row = {"module": "m.py", "line": 1, "operator": "op", "occurrence": 0}
    matrix = {
        "selected": ["a", "b"],
        "mutants": [
            {**row, "covering": ["a", "b", "x"], "killers": ["a", "x"]},
            {**row, "occurrence": 1, "covering": ["b", "x"], "killers": ["b", "x"]},
            {**row, "occurrence": 2, "covering": ["a"], "killers": []},
            {**row, "operator": "thin/ReplaceString", "covering": ["a"], "killers": []},
        ],
    }
    result = thin.verdict(matrix)
    assert set(result["tests"]) == {"a", "b"}
    assert result["minimal"] == []
    assert result["tests"]["a"] == {"verdict": "redundant", "kills": 1, "unique": [], "subsumed_by": "x"}
    assert result["survived"] == ["m.py:1 op#2"]
    assert result["survived_strings"] == ["m.py:1 thin/ReplaceString#0"]


def test_a_test_needed_only_jointly_has_no_single_subsumer():
    row = {"module": "m.py", "line": 1, "operator": "op"}
    matrix = {
        "selected": ["a", "b", "c"],
        "mutants": [
            {**row, "occurrence": 0, "covering": ["a", "b", "c"], "killers": ["a", "b"]},
            {**row, "occurrence": 1, "covering": ["a", "b", "c"], "killers": ["a", "c"]},
            {**row, "occurrence": 2, "covering": ["a", "b", "c"], "killers": ["b", "c"]},
        ],
    }
    result = thin.verdict(matrix)
    assert len(result["minimal"]) == 2
    dropped = next(t for t, entry in result["tests"].items() if entry["verdict"] == "redundant")
    assert result["tests"][dropped]["subsumed_by"] is None


@pytest.fixture
def toy_repo(toy, tmp_path):
    """The toy as a git repository, its first commit the base a branch starts from."""
    run_git(tmp_path, "init", "-q", "-b", "main")
    run_git(tmp_path, "config", "user.email", "t@example.com")
    run_git(tmp_path, "config", "user.name", "t")
    return toy, commit(tmp_path, {}, "base")


def test_changed_lines_are_the_diff_from_base_with_uncommitted_and_untracked_files(toy_repo, tmp_path):
    _, base = toy_repo
    commit(tmp_path, {"lib/kept.py": "a = 1\nb = 2\n", "lib/gone.py": "x = 1\n", "notes.md": "x\n"}, "more")
    (tmp_path / "lib" / "kept.py").write_text("a = 1\nb = 3\nc = 4\n")
    (tmp_path / "lib" / "new.py").write_text("n = 1\nm = 2\no = 3\n")
    (tmp_path / "lib" / "data.txt").write_text("not python\n")
    run_git(tmp_path, "rm", "-q", "lib/gone.py")
    (tmp_path / "age.py").write_text("def adult(age):\n    return age > 18\n")
    assert thin.changed_lines(base, ["lib"]) == {"lib/kept.py": {1, 2, 3}, "lib/new.py": {1, 2, 3}}
    assert thin.changed_lines("HEAD", ["lib"]) == {"lib/kept.py": {2, 3}, "lib/new.py": {1, 2, 3}}
    assert thin.changed_lines(base, ["age.py"]) == {"age.py": {2}}


def test_survivors_runs_an_import_time_line_against_the_whole_suite(toy, tmp_path):
    (tmp_path / "age.py").write_text("LIMIT = 18\ndef adult(age):\n    return age >= LIMIT\n")
    toy["files"]["age.py"]["contexts"] = {"1": [""], "2": [""], "3": [f"{t}|run" for t in TOY_TESTS]}
    result = thin.survivors(toy, {"age.py": {1}}, PYTEST, 60, 2, log=NO_LOG)
    assert result["mutants"] > 0 and result["killed"] == result["mutants"]
    assert result["survivors"] == []


def test_survivors_stops_each_mutant_at_its_first_failing_test(toy, tmp_path, monkeypatch):
    (tmp_path / "test_age.py").write_text(
        textwrap.dedent("""\
            from age import adult

            def test_boundary():
                assert not adult(17)

            def test_later():
                with open("ran.log", "a") as log:
                    log.write("ran\\n")
            """)
    )
    one_mutant(monkeypatch, mutated="def adult(age):\n    return True\n")
    tests = ["test_age.py::test_boundary", "test_age.py::test_later"]
    toy["files"]["age.py"]["contexts"]["2"] = [f"{t}|run" for t in tests]
    result = thin.survivors(toy, {"age.py": {2}}, PYTEST, 60, 1, log=NO_LOG)
    assert result["killed"] == 1
    assert (tmp_path / "ran.log").read_text() == "ran\n"  # the baseline's run only; the mutant's stopped first


@pytest.mark.parametrize(
    ("mutated", "timeout", "outcome"),
    [
        ("import time\ntime.sleep(30)\n", 2, "timeouts"),
        ("import os\nos._exit(3)\n", 60, "crashed"),
        ("raise ImportError('boom')\n", 60, "crashed"),
    ],
    ids=["hang", "no report", "collection error"],
)
def test_survivors_counts_timeouts_and_crashes_apart_from_kills(toy, monkeypatch, mutated, timeout, outcome):
    one_mutant(monkeypatch, mutated=mutated)
    result = thin.survivors(toy, {"age.py": {2}}, PYTEST, timeout, 1, log=NO_LOG)
    assert result[outcome] == 1 and result["killed"] == result["survived"] == 0


def test_main_survivors_lists_an_untested_change_and_exits_1(toy_repo, tmp_path, capsys):
    toy, base = toy_repo
    (tmp_path / "age.py").write_text("def adult(age):\n    return age >= 18\ndef child(age):\n    return age < 13\n")
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    args = ["survivors", "ctx.json", "--base", base, "--paths", "age.py", "--pytest-args", " ".join(PYTEST)]
    assert thin.main(args) == 1
    out = capsys.readouterr()
    result = json.loads(out.out)
    assert result["changed_lines"] == 2 and result["mutants"] == result["survived"] > 0
    assert {row["line"] for row in result["survivors"]} == {4}
    assert all(row.keys() == {"module", "line", "operator", "occurrence", "mutated"} for row in result["survivors"])
    assert not any(row["operator"].startswith(thin.OWN) for row in result["survivors"])  # stock unless asked
    texts = {row["mutated"] for row in result["survivors"]}
    assert {"return age > 13", "return age < 14", "return age < 12"} <= texts and "return age < 13" not in texts
    assert "age.py:4" in out.err


def test_main_survivors_exits_0_when_every_mutant_is_killed(toy_repo, tmp_path, capsys):
    toy, base = toy_repo
    (tmp_path / "age.py").write_text("def adult(age):\n    return age >= 18  # the boundary\n")
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    args = ["survivors", "ctx.json", "--base", base, "--paths", "age.py", "--pytest-args", " ".join(PYTEST)]
    assert thin.main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["mutants"] == result["killed"] > 0


def test_main_survivors_lists_string_survivors_apart_with_thins_operators(toy_repo, tmp_path, capsys):
    toy, base = toy_repo
    (tmp_path / "age.py").write_text("def adult(age):\n    return age >= 18\nLABEL = 'adult'\n")
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    args = ["survivors", "ctx.json", "--base", base, "--paths", "age.py", "--pytest-args", " ".join(PYTEST)]
    assert thin.main(args) == 3
    capsys.readouterr()
    assert thin.main([*args, "--operators", "all"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["survived"] == 0 and result["survivors"] == []
    assert [row["mutated"] for row in result["survived_strings"]] == ["LABEL = ('XX')"]


def test_main_survivors_exits_3_when_changed_lines_make_no_mutant(toy_repo, tmp_path, capsys):
    toy, base = toy_repo
    (tmp_path / "age.py").write_text("# who counts as an adult\ndef adult(age):\n    return age >= 18\n")
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    assert thin.main(["survivors", "ctx.json", "--base", base, "--paths", "age.py"]) == 3
    out = capsys.readouterr()
    assert json.loads(out.out)["mutants"] == 0
    assert "1 changed lines made no mutant" in out.err


def test_main_survivors_exits_2_on_a_base_git_cannot_read_and_requires_base_and_paths(toy_repo, tmp_path, capsys):
    toy, _ = toy_repo
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    assert thin.main(["survivors", "ctx.json", "--base", "no-such-ref", "--paths", "age.py"]) == 2
    assert "thin: git failed: " in capsys.readouterr().err
    for missing in (["--paths", "age.py"], ["--base", "HEAD"]):
        with pytest.raises(SystemExit):
            thin.main(["survivors", "ctx.json", *missing])


def test_main_survivors_exits_2_when_the_baseline_fails(toy_repo, tmp_path, capsys):
    toy, base = toy_repo
    (tmp_path / "age.py").write_text("def adult(age):\n    return age >= 19\n")
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    assert thin.main(["survivors", "ctx.json", "--base", base, "--paths", "age.py"]) == 2
    assert "thin: baseline failed: 2 tests fail unmutated" in capsys.readouterr().err
