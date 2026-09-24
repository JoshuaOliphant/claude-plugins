# ABOUTME: Tests for jev_lint.py: file discovery, rule selection, request fan-out, failure reporting, and CLI exit codes.
# ABOUTME: A stand-in async client replaces Jev; git diff runs against a real temporary repository.
import json
import subprocess

import jev_lint
import pytest
from conftest import FakeJev, noul
from extract import Unit
from rules import COMMENT_KIND, IO_MIXED_WITH_LOGIC, NAME_HIDES_SIDE_EFFECTS, SILENT_FAILURE
from typesafe_sdk import TypeSafeAPIConnectionError

SOURCE = """
def load(path):
    try:
        return open(path).read()
    except Exception:
        pass


def parse(text):
    try:
        return int(text)
    except ValueError:
        return 0
"""


def by_handler(probabilities):
    """Answer silent-failure by which handler is asked about."""

    def answer(state, question_id):
        for fragment, probability in probabilities.items():
            if fragment in state["handler"]:
                return noul(probability)

    return answer


def test_python_files_walks_directories_skips_tooling_dirs_and_dedupes(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("")
    (tmp_path / "pkg" / "notes.txt").write_text("")
    for skipped in (".venv", "node_modules", ".hidden"):
        (tmp_path / skipped).mkdir()
        (tmp_path / skipped / "b.py").write_text("")
    single = tmp_path / "single.py"
    single.write_text("")

    files = jev_lint.python_files([tmp_path / "pkg", single, tmp_path])

    assert files == [tmp_path / "pkg" / "a.py", single]


def test_collect_units_reports_unparseable_and_unreadable_files(tmp_path):
    (tmp_path / "good.py").write_text(SOURCE)
    (tmp_path / "bad.py").write_text("def broken(:\n")
    (tmp_path / "folder.py").mkdir()

    units, skipped = jev_lint.collect_units([tmp_path])

    assert {unit.kind for unit in units} == {"function", "handler"}
    assert [entry.split(":")[0] for entry in skipped] == [
        str(tmp_path / "bad.py"),
        str(tmp_path / "folder.py"),
    ]


def test_select_rules_defaults_to_all_and_rejects_unknown_ids():
    assert jev_lint.select_rules(None) == jev_lint.RULES
    assert jev_lint.select_rules("silent-failure, comment-kind") == [COMMENT_KIND, SILENT_FAILURE]
    with pytest.raises(ValueError, match="unknown rules: nope"):
        jev_lint.select_rules("nope,comment-kind")


@pytest.mark.asyncio
async def test_one_request_per_unit_carries_every_applicable_rule():
    client = FakeJev({"io-mixed-with-logic": noul(0.9), "name-hides-side-effects": noul(0.2)})
    function = Unit("function", "m.py", 3, "load", {"function": "def load(): ..."})
    comment = Unit("comment", "m.py", 1, "# hi", {"comment": "# hi"})
    rules = [IO_MIXED_WITH_LOGIC, NAME_HIDES_SIDE_EFFECTS]

    judgments, failures = await jev_lint.judge_units(client, [function, comment], rules, 4)

    assert failures == []
    assert [(j.rule, j.probability) for j in judgments] == [
        ("io-mixed-with-logic", 0.9),
        ("name-hides-side-effects", 0.2),
    ]
    assert len(client.requests) == 1
    assert list(client.requests[0]["questions"]) == [
        "io-mixed-with-logic",
        "name-hides-side-effects",
    ]


@pytest.mark.asyncio
async def test_failed_units_are_reported_without_losing_finished_judgments():
    def answer(state, question_id):
        if "boom" in state["handler"]:
            raise TypeSafeAPIConnectionError("connection reset")
        if "silent" in state["handler"]:
            return None
        return noul(0.8)

    units = [
        Unit("handler", "m.py", line, name, {"handler": name})
        for line, name in ((1, "ok"), (2, "boom"), (3, "silent"))
    ]

    judgments, failures = await jev_lint.judge_units(FakeJev(answer), units, [SILENT_FAILURE], 4)

    assert [j.name for j in judgments] == ["ok"]
    assert [(f.unit.name, f.error) for f in failures] == [
        ("boom", "connection reset"),
        ("silent", "Jev returned no answer for silent-failure"),
    ]


@pytest.mark.asyncio
async def test_unexpected_errors_are_not_swallowed():
    def answer(state, question_id):
        raise RuntimeError("bug in rule code")

    unit = Unit("handler", "m.py", 1, "h", {"handler": "h"})
    with pytest.raises(RuntimeError, match="bug in rule code"):
        await jev_lint.judge_units(FakeJev(answer), [unit], [SILENT_FAILURE], 4)


def test_format_finding_names_ruff_rules_when_present():
    judgment = jev_lint.Judgment("m.py", 5, "load", "silent-failure", "yes", 0.9, "hides it")
    assert jev_lint.format_finding(judgment) == (
        "m.py:5: silent-failure [yes p=0.90] hides it (load)"
    )
    with_ruff = jev_lint.Judgment(
        "m.py", 5, "load", "silent-failure", "yes", 0.9, "hides it", ("S110",)
    )
    assert jev_lint.format_finding(with_ruff).endswith("(load) [ruff: S110]")


def test_static_rule_summary_counts_each_ruff_rule():
    def finding(*codes):
        return jev_lint.Judgment("m.py", 1, "n", "r", "l", 0.9, "msg", codes)

    assert jev_lint.static_rule_summary([finding()]) == []
    assert jev_lint.static_rule_summary([finding("ERA001"), finding("ERA001", "S110")]) == [
        "Syntactic findings ruff can catch without Jev; add to [tool.ruff.lint] extend-select:",
        "  ERA001: 2 findings",
        "  S110: 1 finding",
    ]


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_git_diff_returns_python_changes_against_ref(tmp_path, monkeypatch):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "Tester")
    (tmp_path / "m.py").write_text("x = 1\n")
    (tmp_path / "notes.md").write_text("a\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    (tmp_path / "m.py").write_text("x = 2\n")
    (tmp_path / "notes.md").write_text("b\n")
    monkeypatch.chdir(tmp_path)

    diff = jev_lint.git_diff("HEAD")

    assert "-x = 1\n+x = 2" in diff
    assert "notes.md" not in diff
    with pytest.raises(jev_lint.GitDiffError, match="no-such-ref"):
        jev_lint.git_diff("no-such-ref")


def test_git_diff_error_falls_back_to_exit_status_when_git_is_silent(monkeypatch):
    def silent_failure(*args, **kwargs):
        raise subprocess.CalledProcessError(128, args[0], stderr="")

    monkeypatch.setattr(jev_lint.subprocess, "run", silent_failure)
    with pytest.raises(jev_lint.GitDiffError, match="git diff HEAD exited 128"):
        jev_lint.git_diff("HEAD")


@pytest.fixture
def cli(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.py").write_text(SOURCE)

    def use(client):
        monkeypatch.setattr(jev_lint, "AsyncTypeSafeClient", lambda: client)
        return client

    return use


def test_main_reports_findings_highest_probability_first(cli, capsys):
    cli(FakeJev(by_handler({"pass": 0.75, "return 0": 0.95})))

    assert jev_lint.main(["--rules", "silent-failure"]) == 1
    assert capsys.readouterr().out.splitlines() == [
        (
            "m.py:12: silent-failure [yes p=0.95] except clause hides the failure from callers "
            "(ValueError)"
        ),
        (
            "m.py:5: silent-failure [yes p=0.75] except clause hides the failure from callers "
            "(Exception) [ruff: BLE001, S110]"
        ),
        "Syntactic findings ruff can catch without Jev; add to [tool.ruff.lint] extend-select:",
        "  BLE001: 1 finding",
        "  S110: 1 finding",
        "2 findings from 2 judgments over 4 units",
    ]


def test_main_flags_at_the_threshold_and_honors_zero_override(cli, capsys):
    cli(FakeJev(by_handler({"pass": 0.7, "return 0": 0.01})))

    assert jev_lint.main(["--rules", "silent-failure"]) == 1
    assert "1 findings from 2 judgments" in capsys.readouterr().out
    assert jev_lint.main(["--rules", "silent-failure", "--threshold", "0"]) == 1
    assert "2 findings from 2 judgments" in capsys.readouterr().out


def test_main_exits_zero_below_every_threshold(cli, capsys):
    cli(FakeJev(by_handler({"pass": 0.69, "return 0": 0.1})))
    assert jev_lint.main(["m.py", "--rules", "silent-failure"]) == 0
    assert capsys.readouterr().out == "0 findings from 2 judgments over 4 units\n"


def test_main_json_prints_every_judgment_and_still_exits_on_findings(cli, capsys):
    cli(FakeJev(by_handler({"pass": 0.9, "return 0": 0.1})))

    assert jev_lint.main(["--rules", "silent-failure", "--json"]) == 1
    judgments = json.loads(capsys.readouterr().out)
    assert set(judgments[0]) == {
        "path",
        "line",
        "name",
        "rule",
        "label",
        "probability",
        "message",
        "static_rules",
    }
    assert {tuple(j["static_rules"]) for j in judgments} == {("BLE001", "S110"), ()}


def test_main_with_only_a_diff_judges_hunks_alone(cli, monkeypatch, capsys):
    hunk_diff = "--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"
    monkeypatch.setattr(jev_lint, "git_diff", lambda ref: hunk_diff)
    client = cli(FakeJev({"symptom-workaround": noul(0.2)}))

    assert jev_lint.main(["--diff", "HEAD", "--rules", "symptom-workaround"]) == 0
    assert client.requests[0]["state"]["added"] == "x = 2"
    assert capsys.readouterr().out == "0 findings from 1 judgments over 1 units\n"


def test_main_skips_without_api_key(cli, monkeypatch, capsys):
    monkeypatch.delenv("TYPESAFE_API_KEY")
    assert jev_lint.main([]) == 3
    assert capsys.readouterr().out == "skipped: TYPESAFE_API_KEY is not set\n"


def test_main_rejects_unknown_rule_even_without_a_key(cli, monkeypatch, capsys):
    monkeypatch.delenv("TYPESAFE_API_KEY")
    with pytest.raises(SystemExit) as exit_info:
        jev_lint.main(["--rules", "nope"])
    assert exit_info.value.code == 2
    assert "unknown rules: nope" in capsys.readouterr().err


def test_main_rejects_missing_paths(cli, capsys):
    assert jev_lint.main(["m.py", "does/not/exist"]) == 4
    assert capsys.readouterr().err == "no such path: does/not/exist\n"


def test_main_refuses_to_report_clean_when_nothing_was_linted(cli, tmp_path, capsys):
    (tmp_path / "empty").mkdir()
    assert jev_lint.main(["empty"]) == 4
    assert capsys.readouterr().err == "nothing to lint: no Python units found\n"


def test_main_reports_git_diff_failure(cli, monkeypatch, capsys):
    def failing_diff(ref):
        raise jev_lint.GitDiffError("fatal: bad revision 'nope'")

    monkeypatch.setattr(jev_lint, "git_diff", failing_diff)
    assert jev_lint.main(["--diff", "nope"]) == 4
    assert capsys.readouterr().err == "git diff failed: fatal: bad revision 'nope'\n"


def test_main_fails_the_run_when_files_were_skipped(cli, tmp_path, capsys):
    (tmp_path / "bad.py").write_text("def broken(:\n")
    cli(FakeJev(by_handler({"pass": 0.9, "return 0": 0.1})))

    assert jev_lint.main(["--rules", "silent-failure"]) == 4
    output = capsys.readouterr()
    assert output.out.splitlines()[-1] == (
        "1 findings from 2 judgments over 4 units; 1 files skipped"
    )
    assert output.err.startswith("skipped bad.py:")


def test_main_reports_units_jev_failed_on(cli, capsys):
    def answer(state, question_id):
        if "pass" in state["handler"]:
            raise TypeSafeAPIConnectionError("connection reset")
        return noul(0.1)

    cli(FakeJev(answer))

    assert jev_lint.main(["--rules", "silent-failure"]) == 2
    output = capsys.readouterr()
    assert output.out == "0 findings from 1 judgments over 4 units; 1 units failed\n"
    assert output.err == "jev failed on m.py:5 (Exception): connection reset\n"


def test_main_reports_jev_unavailable(cli, monkeypatch, capsys):
    def unavailable():
        raise TypeSafeAPIConnectionError("connection refused")

    monkeypatch.setattr(jev_lint, "AsyncTypeSafeClient", unavailable)
    assert jev_lint.main(["--rules", "silent-failure"]) == 2
    assert capsys.readouterr().err == "jev unavailable: connection refused\n"
