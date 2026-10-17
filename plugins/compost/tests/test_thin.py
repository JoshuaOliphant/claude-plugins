# ABOUTME: Tests thin.py: coverage candidates from per-test contexts, the kill matrix run by real cosmic-ray and real
# ABOUTME: pytest in forked children on a toy project, the baseline guard, and the keep / redundant / kills-nothing verdict.
import json
import sys
import textwrap
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


def one_mutant(monkeypatch, line: int = 2, mutated: str | None = "def adult(age):\n    return age > 18\n"):
    """Swap cosmic-ray's mutant list for a single `>=` to `>` on `line`, made as `mutated`."""
    mutant = {"module": "age.py", "operator": "gt", "args": {}, "occurrence": 0, "line": line}
    monkeypatch.setattr(thin, "mutants", lambda module: [mutant])
    monkeypatch.setattr(thin, "mutate", lambda source, m: mutated)


def test_only_limits_mutation_to_the_selected_tests_lines(toy, monkeypatch):
    toy["files"]["other.py"] = {"contexts": {"1": ["test_age.py::test_elsewhere|run"]}}
    only = ["test_age.py::test_grown_up"]
    one_mutant(monkeypatch)
    assert thin.kill_matrix(toy, only, PYTEST, 60, 2, log=NO_LOG) == {
        "selected": only,
        "mutants": [
            {"module": "age.py", "operator": "gt", "occurrence": 0, "line": 2, "covering": TOY_TESTS,
             "killers": ["test_age.py::test_boundary", "test_age.py::test_grown_up"]},
        ],
    }  # fmt: skip
    one_mutant(monkeypatch, line=1)
    assert thin.kill_matrix(toy, only, PYTEST, 60, 2, log=NO_LOG)["mutants"] == []


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


def test_children_read_stdin_from_devnull_so_a_read_cannot_block(toy, tmp_path):
    (tmp_path / "test_stdin.py").write_text("import os\ndef test_reads():\n    assert os.read(0, 1) == b''\n")
    [report] = thin.fork_runs([(None, None, ["test_stdin.py::test_reads"])], PYTEST, 20, 1)
    assert report.named == {"test_stdin.py::test_reads"} and report.failed == set()


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
        (["--no-such-option"], "assert adult(18)", "left no report"),
        (PYTEST, "assert not adult(18)", "1 tests fail unmutated, e.g. test_age.py::test_grown_up"),
        ([*PYTEST, "--junitprefix=pkg"], "assert adult(18)", "never names test_age.py::test_boundary"),
        (PYTEST, "assert adult(18)\nthis is not python", "names a failure no selected test matches: ::test_age"),
    ],
    ids=["broken setup", "red baseline", "junit prefix", "collection error"],
)
@pytest.mark.parametrize(
    "run",
    [
        lambda toy, args: thin.kill_matrix(toy, None, args, 60, 2, log=NO_LOG),
        lambda toy, args: thin.survivors(toy, {"age.py": {2}}, args, 60, 2, log=NO_LOG),
    ],
    ids=["matrix", "survivors"],
)
def test_mutation_refuses_to_run_on_a_baseline_that_is_not_green(toy, tmp_path, pytest_args, test_body, message, run):
    source = (tmp_path / "test_age.py").read_text().replace("assert adult(18)\n", f"{test_body}\n")
    (tmp_path / "test_age.py").write_text(source)
    with pytest.raises(thin.BaselineError, match=message):
        run(toy, pytest_args)


def test_main_runs_each_stage_and_prints_json(toy, tmp_path, capsys, monkeypatch):
    one_mutant(monkeypatch)
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    assert thin.main(["candidates", "ctx.json"]) == 0
    found = json.loads(capsys.readouterr().out)
    assert found["candidates"] == TOY_TESTS
    (tmp_path / "cands.json").write_text(json.dumps(found))
    assert thin.main(["matrix", "ctx.json", "--only", "cands.json", "--pytest-args", " ".join(PYTEST)]) == 0
    out = capsys.readouterr()
    assert "age.py:2 gt#0 killed by 2/3" in out.err
    (tmp_path / "matrix.json").write_text(out.out)
    assert thin.main(["verdict", "matrix.json"]) == 0
    assert json.loads(capsys.readouterr().out)["minimal"] == ["test_age.py::test_boundary"]


def test_main_matrix_takes_node_ids_in_place_of_a_candidates_file(toy, tmp_path, capsys, monkeypatch):
    one_mutant(monkeypatch)
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    args = ["matrix", "ctx.json", "--tests", "test_age.py::test_runs_only", "--workers", "1"]
    assert thin.main([*args, "--pytest-args", " ".join(PYTEST)]) == 0
    assert json.loads(capsys.readouterr().out)["selected"] == ["test_age.py::test_runs_only"]


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
        ],
    }
    result = thin.verdict(matrix)
    assert set(result["tests"]) == {"a", "b"}
    assert result["minimal"] == []
    assert result["tests"]["a"] == {"verdict": "redundant", "kills": 1, "unique": [], "subsumed_by": "x"}
    assert result["survived"] == ["m.py:1 op#2"]


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
