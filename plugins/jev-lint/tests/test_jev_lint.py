# ABOUTME: Tests for jev_lint.py: file discovery, rule selection, request fan-out, and the CLI's output and exit codes.
# ABOUTME: A stand-in async client replaces Jev; git diff runs against a real temporary repository.
import json
import subprocess

import jev_lint
import pytest
from conftest import FakeJev, noul
from extract import Unit
from rules import COMMENT_KIND, SILENT_FAILURE
from typesafe_sdk import TypeSafeAPIConnectionError

SOURCE = """
def load(path):
    try:
        return open(path).read()
    except Exception:
        pass
"""


def test_python_files_walks_directories_and_skips_tooling_dirs(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("")
    (tmp_path / "pkg" / "notes.txt").write_text("")
    for skipped in (".venv", "node_modules", ".hidden"):
        (tmp_path / skipped).mkdir()
        (tmp_path / skipped / "b.py").write_text("")
    single = tmp_path / "single.py"
    single.write_text("")

    files = jev_lint.python_files([tmp_path / "pkg", single, tmp_path])

    assert files == [
        tmp_path / "pkg" / "a.py",
        single,
        tmp_path / "pkg" / "a.py",
        tmp_path / "single.py",
    ]


def test_collect_units_reports_and_skips_unparseable_files(tmp_path, capsys):
    (tmp_path / "good.py").write_text(SOURCE)
    (tmp_path / "bad.py").write_text("def broken(:\n")

    units = jev_lint.collect_units([tmp_path])

    assert {unit.kind for unit in units} == {"function", "handler"}
    assert f"skipped {tmp_path / 'bad.py'}:" in capsys.readouterr().err


def test_select_rules_defaults_to_all_and_rejects_unknown_ids():
    assert jev_lint.select_rules(None) == jev_lint.RULES
    assert jev_lint.select_rules("silent-failure, comment-kind") == [COMMENT_KIND, SILENT_FAILURE]
    with pytest.raises(ValueError, match="unknown rules: nope"):
        jev_lint.select_rules("nope,comment-kind")


@pytest.mark.asyncio
async def test_judge_units_sends_one_request_per_unit_with_applicable_rules():
    client = FakeJev({"silent-failure": noul(0.9)})
    handler = Unit("handler", "m.py", 5, "Exception", {"handler": "except Exception: pass"})
    comment = Unit("comment", "m.py", 1, "# hi", {"comment": "# hi"})

    judgments = await jev_lint.judge_units(client, [handler, comment], [SILENT_FAILURE], 4)

    assert judgments == [
        jev_lint.Judgment(
            "m.py", 5, "Exception", "silent-failure", "yes", 0.9, SILENT_FAILURE.message
        )
    ]
    assert len(client.requests) == 1
    assert client.requests[0]["state"] == handler.state
    assert list(client.requests[0]["questions"]) == ["silent-failure"]


def test_format_finding():
    judgment = jev_lint.Judgment("m.py", 5, "load", "silent-failure", "yes", 0.9, "hides it")
    assert jev_lint.format_finding(judgment) == (
        "m.py:5: silent-failure [yes p=0.90] hides it (load)"
    )


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


@pytest.fixture
def cli(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.py").write_text(SOURCE)

    def use(client):
        monkeypatch.setattr(jev_lint, "AsyncTypeSafeClient", lambda: client)
        return client

    return use


def test_main_reports_findings_sorted_and_exits_one(cli, capsys):
    cli(FakeJev({"silent-failure": noul(0.8)}))
    assert jev_lint.main(["--rules", "silent-failure"]) == 1
    assert capsys.readouterr().out.splitlines() == [
        (
            "m.py:5: silent-failure [yes p=0.80] except clause hides the failure from callers "
            "(Exception)"
        ),
        "1 findings from 1 judgments over 2 units",
    ]


def test_main_exits_zero_below_threshold(cli, capsys):
    cli(FakeJev({"silent-failure": noul(0.8)}))
    assert jev_lint.main(["m.py", "--rules", "silent-failure", "--threshold", "0.9"]) == 0
    assert capsys.readouterr().out == "0 findings from 1 judgments over 2 units\n"


def test_main_json_prints_every_judgment(cli, capsys):
    cli(FakeJev({"silent-failure": noul(0.1)}))
    assert jev_lint.main(["--rules", "silent-failure", "--json"]) == 0
    [judgment] = json.loads(capsys.readouterr().out)
    assert judgment["probability"] == 0.1


def test_main_judges_diff_hunks(cli, monkeypatch, capsys):
    hunk_diff = "--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"
    monkeypatch.setattr(jev_lint, "git_diff", lambda ref: hunk_diff)
    client = cli(FakeJev({"symptom-workaround": noul(0.2)}))

    assert jev_lint.main(["--diff", "HEAD", "--rules", "symptom-workaround"]) == 0
    assert client.requests[0]["state"]["added"] == "x = 2"


def test_main_skips_without_api_key(cli, monkeypatch, capsys):
    monkeypatch.delenv("TYPESAFE_API_KEY")
    assert jev_lint.main([]) == 3
    assert capsys.readouterr().out == "skipped: TYPESAFE_API_KEY is not set\n"


def test_main_rejects_unknown_rule(cli, capsys):
    with pytest.raises(SystemExit) as exit_info:
        jev_lint.main(["--rules", "nope"])
    assert exit_info.value.code == 2
    assert "unknown rules: nope" in capsys.readouterr().err


def test_main_reports_jev_unavailable(cli, capsys):
    cli(FakeJev(error=TypeSafeAPIConnectionError("connection refused")))
    assert jev_lint.main(["--rules", "silent-failure"]) == 2
    assert capsys.readouterr().out == "jev unavailable: connection refused\n"
