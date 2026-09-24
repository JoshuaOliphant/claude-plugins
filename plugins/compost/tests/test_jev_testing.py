# ABOUTME: Tests the suite gatherer (Python and JS/TS test discovery, now and at a git revision) and the testing
# ABOUTME: family's decisions: find-test, duplicate-test, ac-exercised, test-value, and claim-backed.
import asyncio
import json

import pytest
from conftest import StubJev, choice, commit, noul, run_git, score
from jevtools import suite, testing
from jevtools.registry import BadInput

PARAMETRIZED = '''import pytest


@pytest.mark.parametrize("n", [1, 2])
def test_positive(n):
    assert n > 0


class TestEscaping:
    def test_commas_are_quoted(self):
        text = """a,
b"""
        assert text
'''


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_export.py").write_text(
        "def helper():\n    pass\n\n\ndef test_csv_has_header():\n    assert True\n\n\n"
        "class TestEscaping:\n    def test_commas_are_quoted(self):\n        assert True\n\n    def setup(self):\n        pass\n"
    )
    (tmp_path / "tests" / "broken_test.py").write_text("def test_(:\n")
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "list.test.ts").write_text(
        "describe('list', () => {\n  it('sorts by title', () => {\n  })\n})\n"
    )
    (tmp_path / "node_modules" / "dep").mkdir(parents=True)
    (tmp_path / "node_modules" / "dep" / "x.test.js").write_text("test('ignored', () => {})\n")
    return tmp_path


def test_collect_finds_python_functions_class_methods_and_js_tests(repo):
    assert sorted(suite.collect(repo)) == [
        "tests/test_export.py::TestEscaping::test_commas_are_quoted",
        "tests/test_export.py::test_csv_has_header",
        "web/list.test.ts::sorts by title",
    ]
    assert suite.collect(repo)["tests/test_export.py::test_csv_has_header"].startswith("def test_csv_has_header")


def test_a_test_source_keeps_its_decorators_and_drops_its_class_indent():
    tests = suite.tests_in("tests/test_rows.py", PARAMETRIZED)
    assert tests["tests/test_rows.py::test_positive"].startswith('@pytest.mark.parametrize("n", [1, 2])\ndef test')
    assert tests["tests/test_rows.py::TestEscaping::test_commas_are_quoted"] == (
        'def test_commas_are_quoted(self):\n    text = """a,\nb"""\n    assert text'
    )
    assert suite.tests_in("tests/test_rows.py", PARAMETRIZED, limit=10)["tests/test_rows.py::test_positive"] == (
        "@pytest.ma"
    )


@pytest.fixture
def history(tmp_path):
    """A git repo whose suite lives in a subdirectory, committed once as the base."""
    root = tmp_path / "history"
    root.mkdir()
    run_git(root, "init", "-q", "-b", "main")
    run_git(root, "config", "user.email", "t@example.com")
    run_git(root, "config", "user.name", "Tester")
    commit(
        root,
        {
            "plugin/tests/test_cart.py": (
                "def test_total_sums_prices():\n    assert total([2, 3]) == 5\n\n\n"
                "def test_empty_cart_totals_zero():\n    assert total([]) == 0\n"
            ),
            "plugin/tests/helpers.py": "def test_not_collected():\n    pass\n",
        },
        "base",
    )
    return root


def test_collect_at_reads_the_suite_as_it_was_at_a_revision(history):
    base = run_git(history, "rev-parse", "HEAD")
    (history / "plugin" / "tests" / "test_cart.py").write_text("def test_rewritten():\n    assert True\n")
    assert sorted(suite.collect_at(history / "plugin", base)) == [
        "tests/test_cart.py::test_empty_cart_totals_zero",
        "tests/test_cart.py::test_total_sums_prices",
    ]
    with pytest.raises(LookupError, match="'nope' is not a commit"):
        suite.collect_at(history / "plugin", "nope")


def test_gather_needs_criteria_and_tests(repo, tmp_path_factory):
    assert testing.gather_suite({"repo": str(repo), "criterion": "c"})["criteria"] == ["c"]
    with pytest.raises(BadInput, match="needs `criterion` or `criteria`"):
        testing.gather_suite({"repo": str(repo)})
    with pytest.raises(BadInput, match="no tests found"):
        testing.gather_suite({"repo": str(tmp_path_factory.mktemp("empty")), "criteria": ["c"]})


def placing(covered: float, confidence: float = 0.9):
    def answer(tool, state, questions):
        if tool == "find-test/covered":
            return {"covered": noul(covered)}
        options = questions["neighbour"].criteria
        return {"neighbour": choice(next(iter(options)), options, confidence)}

    return answer


@pytest.mark.parametrize(
    ("covered", "action"),
    [(testing.EXTEND_COVERED, "extend"), (testing.EXTEND_COVERED - 0.01, "add-beside")],
    ids=["chosen test covers it", "chosen test does not cover it"],
)
def test_find_test_extends_the_chosen_test_only_when_it_covers_the_criterion(covered, action):
    tests = {"a.py::test_one": "src one" + "x" * 800, "a.py::test_two": "src two", "b.py::test_three": "src three"}
    jev = StubJev(placing(covered))
    result = asyncio.run(testing.find_test(jev, {"criteria": ["c1", "c2"], "tests": tests}))
    assert [p["action"] for p in result["placements"]] == [action, action]
    first = result["placements"][0]
    assert (first["criterion"], first["test"], first["alternatives"]) == (
        "c1",
        "a.py::test_one",
        ["a.py::test_two", "b.py::test_three"],
    )
    choosing, checking = [call for call in jev.calls if call[1]["criterion"] == "c1"]
    assert len(choosing[2]["neighbour"].criteria["a.py::test_one"]) == suite.SOURCE_CHARS
    assert checking[1]["test"] == {"id": "a.py::test_one", "source": tests["a.py::test_one"]}


def test_a_suite_past_the_choice_limit_is_narrowed_by_file_first(monkeypatch):
    monkeypatch.setattr(testing, "CHOICE_LIMIT", 3)
    tests = {f"f{f}.py::test_{n}": "src" for f in range(3) for n in range(2)}

    def answer(tool, state, questions):
        if tool == "find-test/file":
            return {"file": choice("f2.py", questions["file"].criteria)}
        return placing(0.2)(tool, state, questions)

    jev = StubJev(answer)
    result = asyncio.run(testing.find_test(jev, {"criteria": ["c"], "tests": tests}))
    assert jev.calls[0][2]["file"].criteria["f0.py"] == "test_0, test_1"
    assert set(jev.calls[1][2]["neighbour"].criteria) <= set(tests)
    assert len(jev.calls[1][2]["neighbour"].criteria) == 3
    assert result["placements"][0]["action"] == "add-beside"


def test_nearest_ranks_tests_by_shared_rare_words():
    vectors = testing.tfidf(
        {
            "refund": "def test_refund_is_issued(): assert refund(order).issued",
            "refundTwice": "def test_refund_twice(): assert refund(refund(order)).issued",
            "login": "def test_login_rejects_bad_password(): assert not login('x')",
            "empty": "",
        }
    )
    assert [name for name, _ in testing.nearest("refund", vectors, 2)] == ["refundTwice", "login"]
    assert testing.nearest("empty", vectors, 1)[0][1] == 0


def test_gather_changes_pairs_each_added_or_changed_test_with_its_nearest_neighbours(history, monkeypatch):
    monkeypatch.setattr(testing, "NEIGHBOURS", 2)
    tests = history / "plugin" / "tests" / "test_cart.py"
    tests.write_text(
        tests.read_text().replace("== 0", "== 0.0")
        + "\n\ndef test_total_of_two_prices():\n    assert total([4, 1]) == 5\n"
    )
    gathered = testing.gather_changes({"repo": str(history / "plugin"), "base": "main"})
    changes = {change["test"]: change for change in gathered["changes"]}
    assert {node: change["status"] for node, change in changes.items()} == {
        "tests/test_cart.py::test_empty_cart_totals_zero": "changed",
        "tests/test_cart.py::test_total_of_two_prices": "added",
    }
    added = changes["tests/test_cart.py::test_total_of_two_prices"]
    assert added["source"].startswith("def test_total_of_two_prices")
    nearest, farther = added["neighbours"]
    assert (nearest["test"], farther["test"]) == (
        "tests/test_cart.py::test_total_sums_prices",
        "tests/test_cart.py::test_empty_cart_totals_zero",
    )
    assert nearest["similarity"] > farther["similarity"] and gathered["base"] == "main"


@pytest.mark.parametrize(
    ("payload", "message"),
    [({}, "missing base"), ({"base": "nope"}, "'nope' is not a commit")],
)
def test_gather_changes_needs_a_real_base(history, payload, message):
    with pytest.raises(BadInput, match=message):
        testing.gather_changes({"repo": str(history), **payload})


def test_duplicate_test_folds_a_test_into_its_likeliest_duplicate():
    same = {"x.py::test_a": testing.DUPLICATE, "x.py::test_b": 0.9, "x.py::test_c": testing.DUPLICATE - 0.01}
    jev = StubJev(lambda tool, state, questions: {"same_behavior": noul(same[state["existing"]["test"]])})
    change = {
        "test": "x.py::test_new",
        "status": "added",
        "source": "def test_new(): ...",
        "neighbours": [{"test": name, "source": "src", "similarity": 0.4} for name in same],
    }
    alone = {**change, "test": "x.py::test_alone", "neighbours": change["neighbours"][2:]}
    result = asyncio.run(testing.duplicate_test(jev, {"base": "main", "changes": [change, alone]}))
    folded, kept = result["tests"]
    assert folded["recommendation"] == "fold into x.py::test_b"
    assert [d["test"] for d in folded["duplicates"]] == ["x.py::test_b", "x.py::test_a"]
    assert folded["neighbours"][2] == {"test": "x.py::test_c", "same_behavior": 0.49, "similarity": 0.4}
    assert (kept["recommendation"], kept["duplicates"]) == ("keep", [])
    assert jev.calls[0][1]["added"] == {"test": "x.py::test_new", "source": "def test_new(): ..."}


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "needs `criteria`"),
        ({"criteria": []}, "needs `criteria`"),
        ({"criteria": [{"id": "AC-1", "text": "t"}]}, "missing test"),
    ],
)
def test_gather_mapped_needs_criteria_with_a_test_each(repo, payload, message):
    with pytest.raises(BadInput, match=message):
        testing.gather_mapped({"repo": str(repo), **payload})


def test_gather_mapped_reads_each_mapped_test_and_its_parametrized_case(repo):
    gathered = testing.gather_mapped(
        {
            "repo": str(repo),
            "criteria": [
                {"id": "AC-1", "text": "t", "test": "tests/test_export.py::test_csv_has_header[with-bom]"},
                {"id": "AC-2", "text": "t", "test": "tests/test_export.py::test_gone"},
            ],
        }
    )
    header, gone = gathered["criteria"]
    assert (header["case"], header["source"].startswith("def test_csv_has_header")) == ("with-bom", True)
    assert (gone["case"], gone["source"]) == (None, None)


def test_ac_exercised_sends_low_and_unmapped_criteria_to_be_read():
    probability = {"AC-1": testing.EXERCISED, "AC-2": testing.EXERCISED - 0.01}
    jev = StubJev(lambda tool, state, questions: {"asserts_then": noul(probability[state["criterion"]])})
    criteria = [
        {"id": "AC-1", "text": "AC-1", "test": "t.py::test_a[row]", "case": "row", "source": "src"},
        {"id": "AC-2", "text": "AC-2", "test": "t.py::test_b", "case": None, "source": "src"},
        {"id": "AC-3", "text": "AC-3", "test": "t.py::test_gone", "case": None, "source": None},
    ]
    result = asyncio.run(testing.ac_exercised(jev, {"criteria": criteria}))
    assert [(r["exercised"], r["probability"]) for r in result["criteria"]] == [
        (True, 0.5),
        (False, 0.49),
        (False, None),
    ]
    assert result["criteria"][2]["reason"] == "no test with this node id"
    assert result["to_read"] == ["AC-2", "AC-3"]
    assert jev.calls[0][1]["test"] == {"id": "t.py::test_a[row]", "case": "row", "source": "src"}


SHIPPING = """def rate(weight):
    if weight > 30:

        return 'freight'
    return 'parcel'


if __name__ == "__main__":
    print(rate(1))
"""


@pytest.fixture
def code(tmp_path):
    (tmp_path / "shipping.py").write_text(SHIPPING)
    (tmp_path / "broken.py").write_text("def (:\n    x = 1\n")
    (tmp_path / "ship.js").write_text("export const rate = (w) => (w > 30 ? 'freight' : 'parcel')\n")
    return tmp_path


def test_gather_gaps_groups_uncovered_lines_into_blocks_with_context(code):
    uncovered = [
        {"file": "shipping.py", "lines": [9, 2, 4, 8]},
        {"file": "broken.py", "lines": [2]},
        {"file": "ship.js", "lines": [1]},
    ]
    gaps = testing.gather_gaps({"repo": str(code), "uncovered": uncovered})["gaps"]
    assert [(g["file"], g["lines"], g["enclosing"]) for g in gaps] == [
        ("shipping.py", [2, 4], "def rate(weight):"),
        ("shipping.py", [8, 9], None),
        ("broken.py", [2, 2], None),
        ("ship.js", [1, 1], None),
    ]
    assert gaps[0]["excerpt"].splitlines()[:3] == [
        "      1 def rate(weight):",
        ">>    2     if weight > 30:",
        ">>    3 ",
    ]
    assert gaps[0]["excerpt"].splitlines()[-1] == '      8 if __name__ == "__main__":'


def test_gather_gaps_reads_missing_lines_from_a_coverage_report(code):
    report = code / "coverage.json"
    report.write_text(
        json.dumps({"files": {"shipping.py": {"missing_lines": [8, 9]}, "ship.js": {"missing_lines": []}}})
    )
    gaps = testing.gather_gaps({"repo": str(code), "coverage": str(report)})["gaps"]
    assert [(g["file"], g["lines"]) for g in gaps] == [("shipping.py", [8, 9])]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "needs `coverage`"),
        ({"coverage": "absent.json"}, "cannot read coverage report absent.json"),
        ({"uncovered": [{"file": "shipping.py"}]}, "missing lines"),
        ({"uncovered": [{"file": "gone.py", "lines": [1]}]}, "no file .*gone.py"),
    ],
)
def test_gather_gaps_rejects_bad_input(code, payload, message):
    with pytest.raises(BadInput, match=message):
        testing.gather_gaps({"repo": str(code), **payload})


def test_test_value_proposes_an_exclusion_below_the_threshold():
    value = {"a.py": testing.EXCLUDE_BELOW - 0.01, "b.py": testing.EXCLUDE_BELOW}
    jev = StubJev(lambda tool, state, questions: {"value": score(value[state["file"]])})
    gaps = [{"file": name, "lines": [3, 4], "enclosing": None, "excerpt": ">> 3 x"} for name in value]
    result = asyncio.run(testing.test_value(jev, {"gaps": gaps}))
    assert [(b["decision"], b["score"]) for b in result["blocks"]] == [("exclude", 1.49), ("test", 1.5)]
    assert result["exclude"] == ["a.py:3-4"]
    assert result["blocks"][0]["probabilities"] == score(0)["probabilities"]
    assert len(jev.calls[0][2]["value"].criteria) == len(testing.TEST_VALUE_LEVELS)


def test_gather_claims_reads_output_files_and_clips_long_output(tmp_path):
    long = "head\n" + "x" * (testing.OUTPUT_HEAD + testing.OUTPUT_TAIL) + "\n212 passed"
    (tmp_path / "run.txt").write_text(long)
    claims = [{"claim": "212 passed", "output_file": str(tmp_path / "run.txt")}, {"claim": "ok", "output": "ok"}]
    first, second = testing.gather_claims({"claims": claims})["claims"]
    assert first["output"].startswith("head\n") and first["output"].endswith("\n212 passed")
    assert "[... 16 characters clipped ...]" in first["output"]
    assert second == {"claim": "ok", "output": "ok"}


@pytest.mark.parametrize(
    ("claims", "message"),
    [
        (None, "needs `claims`"),
        ([], "needs `claims`"),
        ([{"output": "x"}], "missing claim"),
        ([{"claim": "c"}], "claim 'c' needs `output` or `output_file`"),
        ([{"claim": "c", "output_file": "/absent/run.txt"}], "cannot read /absent/run.txt"),
    ],
)
def test_gather_claims_rejects_bad_input(claims, message):
    with pytest.raises(BadInput, match=message):
        testing.gather_claims({"claims": claims})


def test_claim_backed_lists_the_claims_the_output_does_not_support():
    probability = {"212 passed": testing.BACKED, "coverage 100%": testing.BACKED - 0.01}
    jev = StubJev(lambda tool, state, questions: {"backed": noul(probability[state["claim"]])})
    claims = [{"claim": claim, "output": "212 passed"} for claim in probability]
    result = asyncio.run(testing.claim_backed(jev, {"claims": claims}))
    assert [(c["backed"], c["probability"]) for c in result["claims"]] == [(True, 0.5), (False, 0.49)]
    assert result["unbacked"] == ["coverage 100%"]
