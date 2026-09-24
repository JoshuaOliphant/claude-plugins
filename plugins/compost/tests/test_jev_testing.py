# ABOUTME: Tests the suite gatherer (Python and JS/TS test discovery) and the find-test tool's decisions:
# ABOUTME: extend an existing test only when Jev is confident it already covers the criterion.
import asyncio

import pytest
from conftest import StubJev, choice, noul
from jevtools import suite, testing
from jevtools.registry import BadInput


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


def test_gather_needs_criteria_and_tests(repo, tmp_path_factory):
    assert testing.gather_suite({"repo": str(repo), "criterion": "c"})["criteria"] == ["c"]
    with pytest.raises(BadInput, match="needs `criterion` or `criteria`"):
        testing.gather_suite({"repo": str(repo)})
    with pytest.raises(BadInput, match="no tests found"):
        testing.gather_suite({"repo": str(tmp_path_factory.mktemp("empty")), "criteria": ["c"]})


def placing(covered: float, confidence: float):
    def answer(tool, state, questions):
        options = questions["neighbour"].criteria
        return {"neighbour": choice(next(iter(options)), options, confidence), "covered": noul(covered)}

    return answer


@pytest.mark.parametrize(
    ("covered", "confidence", "action"),
    [(0.9, 0.95, "extend"), (0.9, 0.5, "add-beside"), (0.3, 0.95, "add-beside")],
    ids=["confident and covered", "covered but unsure which test", "not covered"],
)
def test_find_test_extends_only_when_covered_and_confident(covered, confidence, action):
    tests = {"a.py::test_one": "src one", "a.py::test_two": "src two", "b.py::test_three": "src three"}
    jev = StubJev(placing(covered, confidence))
    result = asyncio.run(testing.find_test(jev, {"criteria": ["c1", "c2"], "tests": tests}))
    assert [p["action"] for p in result["placements"]] == [action, action]
    first = result["placements"][0]
    assert (first["criterion"], first["test"], first["alternatives"]) == (
        "c1",
        "a.py::test_one",
        ["a.py::test_two", "b.py::test_three"],
    )


def test_a_suite_past_the_choice_limit_is_narrowed_by_file_first(monkeypatch):
    monkeypatch.setattr(testing, "CHOICE_LIMIT", 3)
    tests = {f"f{f}.py::test_{n}": "src" for f in range(3) for n in range(2)}

    def answer(tool, state, questions):
        if tool == "find-test/file":
            return {"file": choice("f2.py", questions["file"].criteria)}
        options = questions["neighbour"].criteria
        return {"neighbour": choice(next(iter(options)), options), "covered": noul(0.2)}

    jev = StubJev(answer)
    result = asyncio.run(testing.find_test(jev, {"criteria": ["c"], "tests": tests}))
    assert jev.calls[0][2]["file"].criteria["f0.py"] == "test_0, test_1"
    assert set(jev.calls[1][1]["suite"]) <= set(tests) and len(jev.calls[1][1]["suite"]) == 3
    assert result["placements"][0]["action"] == "add-beside"
