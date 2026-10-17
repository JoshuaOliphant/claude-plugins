# ABOUTME: Tests thin.py: coverage candidates from per-test contexts, the kill matrix against a real cosmic-ray and a
# ABOUTME: real pytest run on a toy project, and the keep / redundant / kills-nothing verdict.
import json
import sys
import textwrap

import pytest
import thin

PYTEST = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
COSMIC_RAY = [sys.executable, "-m", "cosmic_ray.cli"]


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
    """The toy's full kill matrix, run once: each mutant costs a cosmic-ray and a pytest process."""
    root = tmp_path_factory.mktemp("toy")
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(root)
        report = make_toy(root)
        return root, thin.kill_matrix(report, None, PYTEST, COSMIC_RAY, 60, log=NO_LOG)


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
    [("tests/test_x.py::test_y[a b]", ("tests.test_x", "test_y[a b]")), ("t.py::TestC::test_y", ("t.TestC", "test_y"))],
    ids=["function", "class"],
)
def test_junit_key_matches_what_pytest_writes(node_id, key):
    assert thin.junit_key(node_id) == key


def test_failing_reads_failures_from_the_junit_report(toy, tmp_path):
    (tmp_path / "age.py").write_text("def adult(age):\n    return age == 18\n")
    assert thin.failing(PYTEST, ["test_age.py::test_boundary", "test_age.py::test_grown_up"], 60) == {
        "test_age.py::test_boundary"
    }


@pytest.mark.parametrize(
    "command",
    [[sys.executable, "-c", "pass"], [sys.executable, "-c", "import time; time.sleep(5)"]],
    ids=["no report", "timeout"],
)
def test_failing_is_none_when_the_run_leaves_no_report(toy, command):
    assert thin.failing(command, ["test_age.py::test_boundary"], 0.5) is None


def test_the_kill_matrix_runs_every_covering_test_and_restores_the_module(toy_matrix):
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


def test_only_limits_mutation_to_the_selected_tests_lines(toy, tmp_path):
    toy["files"]["other.py"] = {"contexts": {"1": ["test_age.py::test_elsewhere|run"]}}
    only = ["test_age.py::test_grown_up"]
    assert thin.kill_matrix(toy, only, PYTEST, fake_cosmic_ray(tmp_path, "gt"), 60, log=NO_LOG) == {
        "selected": only,
        "mutants": [
            {"module": "age.py", "operator": "gt", "occurrence": 0, "line": 2, "covering": TOY_TESTS,
             "killers": ["test_age.py::test_boundary", "test_age.py::test_grown_up"]},
        ],
    }  # fmt: skip
    assert thin.kill_matrix(toy, only, PYTEST, fake_cosmic_ray(tmp_path, "gt", line=1), 60, log=NO_LOG)["mutants"] == []


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


def fake_cosmic_ray(tmp_path, operator: str, line: int = 2) -> list[str]:
    """A stand-in with cosmic-ray's session table and one mutant: `>=` to `>`, or a failed apply."""
    fake = tmp_path / "fake_cr.py"
    fake.write_text(
        textwrap.dedent(f"""\
            import pathlib, sqlite3, sys
            if sys.argv[1] == "init":
                db = sqlite3.connect(sys.argv[3])
                db.execute("CREATE TABLE mutation_specs (operator_name, occurrence, start_pos_row)")
                db.execute("INSERT INTO mutation_specs VALUES ('{operator}', 0, {line})")
                db.commit()
            elif sys.argv[3] == "broken":
                sys.exit(1)
            else:
                path = pathlib.Path(sys.argv[2])
                path.write_text(path.read_text().replace(">=", ">"))
            """)
    )
    return [sys.executable, str(fake)]


def test_a_mutant_that_crashes_the_run_counts_as_killed_by_every_covering_test(toy, tmp_path):
    no_report = [sys.executable, "-c", "pass"]
    matrix = thin.kill_matrix(toy, None, no_report, fake_cosmic_ray(tmp_path, "gt"), 60, log=NO_LOG)
    [row] = matrix["mutants"]
    assert row["crashed"] and row["killers"] == row["covering"] == TOY_TESTS


def test_a_mutant_cosmic_ray_cannot_apply_is_left_out(toy, tmp_path):
    matrix = thin.kill_matrix(toy, None, PYTEST, fake_cosmic_ray(tmp_path, "broken"), 60, log=NO_LOG)
    assert matrix["mutants"] == []


def test_main_runs_each_stage_and_prints_json(toy, tmp_path, capsys):
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    assert thin.main(["candidates", "ctx.json"]) == 0
    found = json.loads(capsys.readouterr().out)
    assert found["candidates"] == TOY_TESTS
    (tmp_path / "cands.json").write_text(json.dumps(found))
    cosmic_ray = " ".join(fake_cosmic_ray(tmp_path, "gt"))
    test_command = " ".join(PYTEST)
    args = ["matrix", "ctx.json", "--only", "cands.json", "--cosmic-ray", cosmic_ray, "--test-command", test_command]
    assert thin.main(args) == 0
    out = capsys.readouterr()
    assert "age.py:2 gt#0 killed by 2/3" in out.err
    (tmp_path / "matrix.json").write_text(out.out)
    assert thin.main(["verdict", "matrix.json"]) == 0
    assert json.loads(capsys.readouterr().out)["minimal"] == ["test_age.py::test_boundary"]


def test_main_matrix_takes_node_ids_in_place_of_a_candidates_file(toy, tmp_path, capsys):
    (tmp_path / "ctx.json").write_text(json.dumps(toy))
    cosmic_ray = " ".join(fake_cosmic_ray(tmp_path, "gt"))
    args = ["matrix", "ctx.json", "--tests", "test_age.py::test_runs_only", "--cosmic-ray", cosmic_ray]
    assert thin.main([*args, "--test-command", " ".join(PYTEST)]) == 0
    assert json.loads(capsys.readouterr().out)["selected"] == ["test_age.py::test_runs_only"]
