# ABOUTME: Tests for evals/run_eval.py: case-to-unit conversion, comment records, scoring, and the printed report.
# ABOUTME: A stand-in for jev_lint.run replaces the live API, so these tests cost nothing and stay deterministic.
import json

import pytest
import run_eval
from jev_lint import Failure, Judgment


def judgments_for(units, probability=0.9, label="yes"):
    return [
        Judgment(unit.path, unit.line, unit.name, "silent-failure", label, probability, "msg")
        for unit in units
    ]


@pytest.fixture
def fake_run(monkeypatch):
    def use(judgments_of=judgments_for, failures=()):
        async def run(units, rules, concurrency):
            return judgments_of(units), list(failures)

        monkeypatch.setattr(run_eval, "run", run)

    return use


def test_source_case_becomes_a_unit_tagged_with_its_case_index():
    case = {"rule": "silent-failure", "flag": True, "source": "try:\n    x()\nexcept:\n    pass\n"}
    unit = run_eval.unit_for_case(3, case)
    assert (unit.kind, unit.path) == ("handler", "case3/app/example.py")


def test_diff_case_becomes_a_hunk_unit():
    diff = "--- a/tests/test_x.py\n+++ b/tests/test_x.py\n@@ -1 +1 @@\n-    assert x == 1\n+    assert x\n"
    unit = run_eval.unit_for_case(0, {"rule": "test-weakening", "flag": True, "diff": diff})
    assert (unit.kind, unit.path) == ("hunk", "case0/tests/test_x.py")


def test_case_without_a_matching_unit_names_the_case():
    case = {"rule": "silent-failure", "flag": True, "source": "x = 1\n"}
    with pytest.raises(ValueError, match="case 7 \\(silent-failure\\) contains no handler unit"):
        run_eval.unit_for_case(7, case)


def test_comment_records_become_labeled_cases(tmp_path):
    record = {
        "repo": "demo",
        "sha": "abc123",
        "path": "pkg/m.py",
        "line": 4,
        "comment": "# sort the rows",
        "context_before": "rows = load()",
        "context_after": "return rows",
        "label": "deleted",
    }
    path = tmp_path / "comments.jsonl"
    path.write_text(json.dumps(record) + "\n" + json.dumps({**record, "label": "kept"}) + "\n")

    deleted, kept = run_eval.comment_cases(path)

    assert deleted.should_flag and not kept.should_flag
    assert deleted.unit.path == "deleted/demo@abc123/pkg/m.py"
    assert deleted.unit.state["code_before"] == "rows = load()"
    assert deleted.source == "demo@abc123 # sort the rows"


def _case(path, should_flag=True, rule_id="silent-failure"):
    unit = run_eval.Unit("handler", path, 1, path, {"handler": "except: pass"})
    return run_eval.LabeledCase(unit, should_flag, path, rule_id)


@pytest.mark.asyncio
async def test_judge_pairs_each_case_with_its_judgment(fake_run):
    fake_run()
    scored = await run_eval.judge([_case("a"), _case("b", should_flag=False)])
    assert [(row.source, row.should_flag, row.probability) for row in scored] == [
        ("a", True, 0.9),
        ("b", False, 0.9),
    ]


@pytest.mark.asyncio
async def test_judge_refuses_cases_that_share_a_path_and_line(fake_run):
    fake_run()
    with pytest.raises(ValueError, match="share a path and line"):
        await run_eval.judge([_case("a"), _case("a")])


@pytest.mark.asyncio
async def test_judge_stops_when_jev_failed_rather_than_scoring_a_partial_run(fake_run):
    case = _case("a")
    fake_run(judgments_of=lambda units: [], failures=[Failure(case.unit, "connection reset")])
    with pytest.raises(RuntimeError, match="Jev failed on 1 silent-failure cases"):
        await run_eval.judge([case])


def test_report_prints_precision_recall_and_the_disagreements(capsys):
    scored = [
        run_eval.Scored("silent-failure", True, 0.95, "yes", "caught"),
        run_eval.Scored("silent-failure", False, 0.80, "yes", "false alarm here"),
        run_eval.Scored("silent-failure", True, 0.20, "yes", "missed here"),
    ]

    run_eval.report(scored)

    lines = capsys.readouterr().out.splitlines()
    assert lines[1] == "== silent-failure: 3 cases, 2 should flag =="
    assert lines[2] == "  threshold 0.5: flagged   2  precision 0.50  recall 0.50"
    assert lines[4] == "  threshold 0.9: flagged   1  precision 1.00  recall 0.50"
    assert lines[5:] == [
        "    false alarm p=0.80 [yes] false alarm here",
        "    missed      p=0.20 [yes] missed here",
    ]


def test_report_handles_a_rule_with_no_positive_cases(capsys):
    run_eval.report([run_eval.Scored("silent-failure", False, 0.1, "yes", "clean")])
    assert "precision nan  recall nan" in capsys.readouterr().out


def test_main_scores_the_bundled_cases(fake_run, monkeypatch, capsys):
    monkeypatch.setattr(
        run_eval,
        "CASES",
        [{"rule": "silent-failure", "flag": True, "source": "try:\n    x()\nexcept:\n    pass\n"}],
    )
    monkeypatch.setattr(run_eval.sys, "argv", ["run_eval.py"])
    fake_run()

    run_eval.main()

    output = capsys.readouterr().out
    assert "== silent-failure: 1 cases, 1 should flag ==" in output
    assert "1 judgments in " in output


def test_main_also_scores_a_comments_file(fake_run, monkeypatch, tmp_path, capsys):
    record = {
        "repo": "demo",
        "sha": "abc123",
        "path": "pkg/m.py",
        "line": 4,
        "comment": "# sort the rows",
        "context_before": "rows = load()",
        "context_after": "return rows",
        "label": "deleted",
    }
    comments = tmp_path / "comments.jsonl"
    comments.write_text(json.dumps(record) + "\n")
    monkeypatch.setattr(run_eval, "CASES", [])
    monkeypatch.setattr(run_eval.sys, "argv", ["run_eval.py", str(comments)])
    fake_run()

    run_eval.main()

    assert "== comment-kind: 1 cases, 1 should flag ==" in capsys.readouterr().out


def test_main_refuses_a_comments_file_that_does_not_exist(monkeypatch):
    monkeypatch.setattr(run_eval.sys, "argv", ["run_eval.py", "missing.jsonl"])
    with pytest.raises(SystemExit, match="no such comments file: missing.jsonl"):
        run_eval.main()
