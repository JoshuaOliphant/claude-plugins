"""
ABOUTME: Tests for superfan.py: config guards, prompt assembly, the run loop, verdicts, launchd.
ABOUTME: claude, notifiers, and launchctl are replaced by fakes; nothing leaves the process.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import superfan  # noqa: E402

TOOLS = ["mcp__prometheus__query", "mcp__splunk__search"]
# A Tuesday inside the default active hours.
NOW = datetime(2026, 10, 13, 10, 0)


@pytest.fixture(autouse=True)
def sf_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERFAN_HOME", str(tmp_path / "sf"))
    monkeypatch.setattr(superfan, "LAUNCH_AGENTS", tmp_path / "LaunchAgents")
    return tmp_path / "sf"


@pytest.fixture
def notified(monkeypatch):
    calls = []
    monkeypatch.setitem(superfan.NOTIFIERS, "stdout", lambda cfg, *a: calls.append(a))
    return calls


def make(component="orders-api", **overrides):
    d = superfan.init(component)
    settings = {"allowed_tools": TOOLS, "notify": "stdout", **overrides}
    lines = [f"{k} = {json.dumps(v)}" for k, v in settings.items()]
    (d / "superfan.toml").write_text("\n".join(lines) + "\n")
    return superfan.load_config(component)


def envelope(findings=(), status="healthy", baselines=None, **extra):
    report = {"status": status, "summary": "all quiet", "findings": list(findings)}
    if baselines is not None:
        report["baselines"] = baselines
    return json.dumps(
        {"is_error": False, "total_cost_usd": 0.05, "structured_output": report, **extra}
    )


def fake_claude(stdout, returncode=0, stderr=""):
    seen = {}

    def runner(argv, **kwargs):
        seen["argv"], seen["kwargs"] = argv, kwargs
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)

    runner.seen = seen
    return runner


def finding(fp="lag-orders", severity="page", title="Consumer lag climbing"):
    return {
        "same_as": None,
        "fingerprint": fp,
        "title": title,
        "severity": severity,
        "evidence": ["sum(kafka_lag) = 9000 vs baseline 200"],
        "suspected_cause": "slow consumer",
        "next_checks": ["check rebalances"],
    }


# --- config ------------------------------------------------------------------------------


def test_init_writes_templates_and_is_idempotent(sf_home):
    d = superfan.init("orders-api")
    assert "orders-api" in (d / "charter.md").read_text()
    (d / "charter.md").write_text("mine")
    superfan.init("orders-api")
    assert (d / "charter.md").read_text() == "mine"
    assert {p.name for p in d.iterdir()} >= {"inbox", "closed", "digest", "runs"}


@pytest.mark.parametrize("name", ["Orders", "bin", "-x", "a b"])
def test_init_rejects_bad_names(name):
    with pytest.raises(superfan.SuperfanError):
        superfan.init(name)


def test_load_config_missing_component():
    with pytest.raises(superfan.SuperfanError, match="run init"):
        superfan.load_config("nope")


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"allowed_tools": []}, "blind"),
        ({"allowed_tools": ["mcp__kubernetes"]}, "exact read-only"),
        ({"allowed_tools": ["mcp__kubernetes__*"]}, "exact read-only"),
        ({"notify": "teams"}, "notify must be"),
        ({"notify": "command"}, "needs notify_command"),
        ({"active_days": ["monday"]}, "active_days"),
        ({"active_hours": "9-5"}, "HH:MM"),
        ({"surprise": 1}, "unknown keys"),
    ],
)
def test_load_config_rejects(overrides, message):
    with pytest.raises(superfan.SuperfanError, match=message):
        make(**overrides)


def test_template_config_loads_once_tools_are_filled_in(sf_home):
    d = superfan.init("orders-api")
    text = (
        (d / "superfan.toml")
        .read_text()
        .replace("allowed_tools = []", f"allowed_tools = {json.dumps(TOOLS)}")
    )
    (d / "superfan.toml").write_text(text)
    cfg = superfan.load_config("orders-api")
    assert cfg.notify == "terminal-notifier" and cfg.active_hours == "08:00-18:00"


@pytest.mark.parametrize(
    "when, active",
    [
        (NOW, True),
        (NOW.replace(hour=7, minute=59), False),
        (NOW.replace(hour=18), False),
        (NOW + timedelta(days=4), False),  # Saturday
    ],
)
def test_is_active(when, active):
    assert superfan.is_active(make(), when) is active


def test_is_active_all_day():
    cfg = make()
    cfg.active_hours = None
    assert superfan.is_active(cfg, NOW.replace(hour=3))


# --- prompt ------------------------------------------------------------------------------


def test_prompt_carries_charter_open_findings_verdicts_and_neighbors(sf_home):
    broker = make("kafka-broker")
    superfan.record_findings(broker, sf_home / "kafka-broker", NOW, [finding("isr-shrink")])
    superfan.record_findings(
        broker, sf_home / "kafka-broker", NOW - timedelta(days=2), [finding("old-thing")]
    )
    cfg = make(neighbors=["kafka-broker"])
    d = sf_home / "orders-api"
    (d / "charter.md").write_text("CHARTER-TEXT")
    superfan.record_findings(cfg, d, NOW, [finding("lag-orders", severity="digest")])
    (d / "ledger.jsonl").write_text(
        json.dumps({"fingerprint": "batch-spike", "verdict": "known", "note": "nightly"}) + "\n"
    )

    prompt = superfan.build_prompt(cfg, NOW)

    assert "You are the orders-api superfan" in prompt
    assert "CHARTER-TEXT" in prompt
    assert "`lag-orders` Consumer lag climbing" in prompt
    assert "`batch-spike`  -> known: nightly" in prompt
    assert "kafka-broker: [page] Consumer lag climbing" in prompt
    assert prompt.count("kafka-broker:") == 1  # the two-day-old finding is out of the window


def test_prompt_without_history():
    prompt = superfan.build_prompt(make(neighbors=["not-set-up-yet"]), NOW)
    assert "No baselines yet." not in prompt  # init seeds the file
    assert "None." in prompt
    assert "neighboring superfans saw in the last 24h\n\nNone." in prompt


# --- argv --------------------------------------------------------------------------------


def test_claude_argv_is_read_only(sf_home):
    argv = superfan.claude_argv(make(mcp_config="~/x.json"))
    assert argv[argv.index("--tools") + 1] == ""
    assert argv[argv.index("--permission-mode") + 1] == "dontAsk"
    i = argv.index("--allowedTools")
    assert argv[i + 1 : i + 3] == TOOLS
    assert "--strict-mcp-config" in argv
    assert json.loads(argv[argv.index("--json-schema") + 1]) == superfan.REPORT_SCHEMA


# --- parse -------------------------------------------------------------------------------


def test_parse_report_prefers_structured_output():
    report, env = superfan.parse_report(envelope([finding()]))
    assert report["findings"][0]["fingerprint"] == "lag-orders"
    assert env["total_cost_usd"] == 0.05


def test_parse_report_falls_back_to_result_text():
    report, _ = superfan.parse_report(
        json.dumps({"result": json.dumps({"status": "healthy", "summary": "", "findings": []})})
    )
    assert report["status"] == "healthy"


@pytest.mark.parametrize(
    "stdout",
    [
        "not json",
        json.dumps({"is_error": True, "result": "budget"}),
        json.dumps({"result": "prose"}),
        json.dumps({"structured_output": {"status": "healthy"}}),
    ],
)
def test_parse_report_failures(stdout):
    with pytest.raises(superfan.RunFailed):
        superfan.parse_report(stdout)


# --- run ---------------------------------------------------------------------------------


def test_run_healthy_writes_heartbeat_and_raw_output(sf_home, notified, capsys):
    cfg = make()
    runner = fake_claude(envelope())
    assert superfan.run(cfg, NOW, runner) == 0
    d = sf_home / "orders-api"
    assert runner.seen["kwargs"]["cwd"] == d
    assert "Charter" in runner.seen["kwargs"]["input"]
    digest = (d / "digest" / "2026-10-13.md").read_text()
    assert "10:00 healthy $0.050: all quiet" in digest
    assert len(list((d / "runs").glob("*.json"))) == 1
    assert notified == []


def test_run_skips_outside_active_hours(sf_home):
    runner = fake_claude(envelope())
    assert superfan.run(make(), NOW.replace(hour=22), runner) == 0
    assert "argv" not in runner.seen


def test_run_pages_digests_and_dedupes(sf_home, notified):
    cfg = make()
    d = sf_home / "orders-api"
    found = [finding("lag-orders"), finding("gc-pauses", severity="digest", title="GC creep")]
    superfan.run(cfg, NOW, fake_claude(envelope(found, status="anomalous")))

    assert len(notified) == 1
    title, body, finding_id = notified[0]
    assert title == "orders-api: Consumer lag climbing" and "9000" in body
    assert (d / "inbox" / f"{finding_id}.md").exists()
    assert "GC creep" in (d / "digest" / "2026-10-13.md").read_text()

    later = NOW + timedelta(hours=1)
    superfan.run(cfg, later, fake_claude(envelope(found, status="anomalous")))
    assert len(notified) == 1  # same fingerprints: no second page
    meta = superfan.read_finding(d / "inbox" / f"{finding_id}.md")
    assert meta["seen"] == "2" and meta["last_seen"] == later.isoformat(timespec="seconds")
    assert "repeats 2" in (d / "digest" / "2026-10-13.md").read_text()


def test_run_rewrites_baselines_with_backup(sf_home, notified):
    d = sf_home / "orders-api"
    cfg = make()
    old = (d / "baselines.md").read_text()
    superfan.run(cfg, NOW, fake_claude(envelope(baselines="# new normal")))
    assert (d / "baselines.md").read_text() == "# new normal\n"
    assert (d / "baselines.md.bak").read_text() == old


def test_run_reports_denied_tools(sf_home, notified):
    stdout = envelope(permission_denials=[{"tool_name": "mcp__kubernetes__delete_pod"}])
    superfan.run(make(), NOW, fake_claude(stdout))
    assert (
        "1 tool calls denied" in (sf_home / "orders-api" / "digest" / "2026-10-13.md").read_text()
    )


def test_blind_superfan_notifies_once_after_threshold(sf_home, notified):
    cfg = make(failure_alert_after=2)
    broken = fake_claude("", returncode=1, stderr="auth expired")
    assert superfan.run(cfg, NOW, broken) == 1
    assert notified == []
    superfan.run(cfg, NOW, broken)
    superfan.run(cfg, NOW, broken)
    assert len(notified) == 1 and "is blind" in notified[0][0]
    assert "FAILED" in (sf_home / "orders-api" / "digest" / "2026-10-13.md").read_text()
    superfan.run(cfg, NOW, fake_claude(envelope()))
    assert superfan.load_state(sf_home / "orders-api") == {"failures": 0}


def test_run_survives_timeout(sf_home, notified):
    def slow(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 1)

    assert superfan.run(make(), NOW, slow) == 1


# --- verdicts ----------------------------------------------------------------------------


def _page_one(cfg, notified, now=NOW, fp="lag-orders"):
    superfan.run(cfg, now, fake_claude(envelope([finding(fp)])))
    return notified[-1][2]


def test_known_verdict_silences_for_good(sf_home, notified):
    cfg = make()
    fid = _page_one(cfg, notified)
    dest = superfan.verdict("orders-api", fid, "known", "nightly batch", NOW)
    assert dest.parent.name == "closed"
    entry = superfan.read_ledger(sf_home / "orders-api")[0]
    assert entry["verdict"] == "known" and entry["severity"] == "page"

    later = NOW + timedelta(weeks=9)  # stays a Tuesday, so the run is not skipped
    runner = fake_claude(envelope([finding(), finding("other-thing")]))
    superfan.run(cfg, later, runner)
    assert "argv" in runner.seen
    assert [n[0] for n in notified] == [
        "orders-api: Consumer lag climbing",
        "orders-api: Consumer lag climbing",  # other-thing pages; lag-orders does not
    ]
    assert len(list((sf_home / "orders-api" / "inbox").glob("*lag-orders*"))) == 0


def test_same_as_overrides_a_reworded_fingerprint(sf_home, notified):
    cfg = make()
    fid = _page_one(cfg, notified)
    superfan.verdict("orders-api", fid, "known", "", NOW)
    assert "Consumer lag climbing -> known" in superfan.build_prompt(cfg, NOW)
    reworded = {**finding("lag-stuck-after-batch"), "same_as": "lag-orders"}
    superfan.run(cfg, NOW + timedelta(hours=1), fake_claude(envelope([reworded])))
    assert len(notified) == 1


def test_noise_verdict_expires(sf_home, notified):
    cfg = make(suppress_noise_days=7)
    fid = _page_one(cfg, notified)
    superfan.verdict("orders-api", fid, "noise", "", NOW)
    superfan.run(cfg, NOW + timedelta(days=1), fake_claude(envelope([finding()])))
    assert len(notified) == 1
    _page_one(cfg, notified, now=NOW + timedelta(days=8))
    assert len(notified) == 2


def test_verdict_errors(notified):
    cfg = make()
    with pytest.raises(superfan.SuperfanError, match="must be one of"):
        superfan.verdict("orders-api", "x", "meh", "", NOW)
    with pytest.raises(superfan.SuperfanError, match="no open finding"):
        superfan.verdict("orders-api", "x", "real", "", NOW)
    assert cfg


def test_stats_reports_cost_and_page_precision(sf_home, notified):
    cfg = make()
    a = _page_one(cfg, notified, fp="a")
    b = _page_one(cfg, notified, now=NOW + timedelta(minutes=1), fp="b")
    superfan.verdict("orders-api", a, "real", "", NOW)
    superfan.verdict("orders-api", b, "noise", "", NOW)
    (sf_home / "orders-api" / "runs" / "garbage.json").write_text("{")
    s = superfan.stats("orders-api")
    assert s["runs"] == 3 and s["failed_runs"] == 1
    assert s["cost_usd"] == 0.1
    assert s["page_precision"] == 0.5
    assert s["verdicts"] == {"real": 1, "noise": 1, "known": 0}


def test_stats_empty():
    make()
    assert superfan.stats("orders-api")["page_precision"] is None


# --- notifiers ---------------------------------------------------------------------------


@pytest.fixture
def ran(monkeypatch):
    calls = []
    monkeypatch.setattr(superfan.subprocess, "run", lambda *a, **k: calls.append((a, k)))
    return calls


def test_terminal_notifier_click_opens_triage(ran):
    cfg = make(notify="terminal-notifier")
    superfan.notify(cfg, "t", "b", "F1")
    argv = ran[0][0][0]
    assert argv[0] == "terminal-notifier"
    assert argv[-2] == "-execute" and argv[-1].endswith("open orders-api F1")
    superfan.notify(cfg, "t", "b", None)
    assert "-execute" not in ran[1][0][0]


def test_osascript_notifier(ran):
    superfan.notify(make(notify="osascript"), 't"x', "b", None)
    assert ran[0][0][0][:2] == ["osascript", "-e"] and '\\"' in ran[0][0][0][2]


def test_command_notifier_passes_env(ran):
    superfan.notify(make(notify="command", notify_command="echo hi"), "t", "b", "F1")
    (args, kwargs) = ran[0]
    assert args[0] == "echo hi" and kwargs["shell"]
    assert kwargs["env"]["SUPERFAN_FINDING"] == "F1"


def test_stdout_notifier(capsys):
    superfan._notify_stdout(make(), "t", "b", "F1")
    assert "NOTIFY t: b [F1]" in capsys.readouterr().out


def test_open_triage_runs_claude_in_terminal(ran, sf_home):
    superfan.open_triage("orders-api", "F1")
    script = ran[0][0][0][2]
    assert "Terminal" in script and "/superfan:triage orders-api F1" in script


# --- launchd -----------------------------------------------------------------------------


def test_install_copies_runner_and_writes_plist(sf_home, tmp_path, monkeypatch):
    make(cadence_minutes=30)
    monkeypatch.setenv("PATH", "/opt/homebrew/bin:/usr/bin")
    calls = []
    path = superfan.install("orders-api", load=True, runner=lambda a, **k: calls.append(a))
    text = path.read_text()
    assert path == tmp_path / "LaunchAgents" / "com.superfan.orders-api.plist"
    assert "<integer>1800</integer>" in text
    assert "/opt/homebrew/bin:/usr/bin" in text
    assert str(sf_home / "bin" / "superfan.py") in text
    assert (sf_home / "bin" / "watch_prompt.md").exists()
    assert [c[1] for c in calls] == ["bootout", "bootstrap"]


def test_install_without_load(sf_home):
    make()
    calls = []
    superfan.install("orders-api", load=False, runner=lambda a, **k: calls.append(a))
    assert calls == []


def test_uninstall(sf_home):
    make()
    superfan.install("orders-api", load=False)
    calls = []
    path = superfan.uninstall("orders-api", runner=lambda a, **k: calls.append(a))
    assert not path.exists() and calls[0][1] == "bootout"


# --- cli ---------------------------------------------------------------------------------


def test_cli_init_stats_and_errors(sf_home, capsys):
    assert superfan.main(["init", "orders-api"]) == 0
    assert superfan.main(["run", "orders-api"]) == 2  # empty allowed_tools
    assert "blind" in capsys.readouterr().err
    make()
    assert superfan.main(["stats", "orders-api"]) == 0
    assert '"runs": 0' in capsys.readouterr().out
    assert superfan.main(["verdict", "orders-api", "x", "real"]) == 2


def test_cli_dispatches(monkeypatch, sf_home):
    make()
    seen = []
    monkeypatch.setattr(superfan, "run", lambda cfg, now: seen.append("run") or 0)
    monkeypatch.setattr(superfan, "install", lambda c, load: seen.append(("install", load)))
    monkeypatch.setattr(superfan, "uninstall", lambda c: seen.append("uninstall"))
    monkeypatch.setattr(superfan, "notify", lambda *a: seen.append("notify"))
    monkeypatch.setattr(superfan, "open_triage", lambda c, f: seen.append(("open", f)))
    for argv in (
        ["run", "orders-api"],
        ["install", "orders-api", "--load"],
        ["uninstall", "orders-api"],
        ["notify-test", "orders-api"],
        ["open", "orders-api", "F1"],
    ):
        assert superfan.main(argv) == 0
    assert seen == ["run", ("install", True), "uninstall", "notify", ("open", "F1")]
