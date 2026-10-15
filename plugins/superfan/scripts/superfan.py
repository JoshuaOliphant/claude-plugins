#!/usr/bin/env python3
# ABOUTME: Runs a superfan: one headless Claude watching one component's telemetry on a schedule.
# ABOUTME: Owns the prompt, the tool allowlist, the inbox/ledger/digest files, notification, launchd.
"""superfan: one Claude, one component, nothing better to do than refresh charts.

Every file a superfan owns lives in ``$SUPERFAN_HOME/<component>/`` (default
``~/.superfans``)::

    superfan.toml   cadence, model, budget, the read-only tool allowlist, notifier
    charter.md      what the component is, what healthy looks like, its queries
    baselines.md    observed normal, rewritten by the superfan as it learns
    ledger.jsonl    one line per human verdict on a finding (real | noise | known)
    inbox/          open findings, one markdown file each
    closed/         findings that have a verdict
    digest/         one file per day: a heartbeat per run plus every digest-level finding
    runs/           the raw ``claude -p`` result of each run, for debugging and cost
    state.json      consecutive failure count

The model never touches these files. A run gives it read-only MCP tools and no built-in
tools at all; it answers with JSON matching ``REPORT_SCHEMA`` and this script does the
writing, deduplication, and notification deterministically.

Commands:
    init <component>                           create the directory from templates
    run <component>                            one watch pass
    verdict <component> <finding-id> <verdict> [--note TEXT]
    stats <component>                          runs, cost, findings, noise rate
    install <component> [--load]               write (and load) the launchd agent
    uninstall <component>                      unload and remove the launchd agent
    notify-test <component>                    fire a test notification
    open <component> <finding-id>              open a terminal on /superfan:triage
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = PLUGIN_ROOT / "templates"
WATCH_PROMPT = Path(__file__).resolve().parent / "watch_prompt.md"
LAUNCH_AGENTS = Path("~/Library/LaunchAgents").expanduser()
VERDICTS = ("real", "noise", "known")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
# An exact MCP tool name. A bare server prefix or a wildcard would also allow that server's
# write tools (a Kubernetes server's delete_pod), so the allowlist accepts names only.
TOOL_NAME = re.compile(r"^mcp__[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+$")
RECENT_VERDICTS = 30
NEIGHBOR_HOURS = 24

REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["healthy", "watching", "anomalous", "blind"]},
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "same_as": {"type": ["string", "null"]},
                    "fingerprint": {"type": "string"},
                    "title": {"type": "string"},
                    "severity": {"type": "string", "enum": ["page", "digest"]},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "suspected_cause": {"type": "string"},
                    "next_checks": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["same_as", "fingerprint", "title", "severity", "evidence"],
            },
        },
        "baselines": {"type": ["string", "null"]},
    },
    "required": ["status", "summary", "findings"],
}


class SuperfanError(Exception):
    """A problem the user has to fix: bad config, missing component."""


class RunFailed(Exception):
    """The headless run produced nothing usable; the superfan is blind this pass."""


@dataclass
class Config:
    component: str
    allowed_tools: list[str]
    cadence_minutes: int = 60
    model: str = "sonnet"
    max_budget_usd: float = 1.0
    timeout_seconds: int = 900
    mcp_config: str | None = None
    notify: str = "terminal-notifier"
    notify_command: str | None = None
    active_hours: str | None = "08:00-18:00"
    active_days: list[str] = field(default_factory=lambda: list(DAYS[:5]))
    suppress_noise_days: int = 7
    failure_alert_after: int = 3
    neighbors: list[str] = field(default_factory=list)


def home() -> Path:
    return Path(os.environ.get("SUPERFAN_HOME", "~/.superfans")).expanduser()


def component_dir(component: str) -> Path:
    return home() / component


def load_config(component: str) -> Config:
    path = component_dir(component) / "superfan.toml"
    if not path.exists():
        raise SuperfanError(f"no superfan named {component!r}: {path} is missing (run init)")
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    known = set(Config.__dataclass_fields__) - {"component"}
    unknown = set(raw) - known
    if unknown:
        raise SuperfanError(f"{path}: unknown keys {sorted(unknown)}")
    cfg = Config(component=component, **{"allowed_tools": [], **raw})
    if not cfg.allowed_tools:
        raise SuperfanError(f"{path}: allowed_tools is empty; the superfan would be blind")
    bad = [t for t in cfg.allowed_tools if not TOOL_NAME.match(t)]
    if bad:
        raise SuperfanError(
            f"{path}: allowed_tools must be exact read-only MCP tool names "
            f"(mcp__<server>__<tool>), not {bad}"
        )
    if cfg.notify not in NOTIFIERS:
        raise SuperfanError(f"{path}: notify must be one of {sorted(NOTIFIERS)}")
    if cfg.notify == "command" and not cfg.notify_command:
        raise SuperfanError(f"{path}: notify = 'command' needs notify_command")
    bad_days = [d for d in cfg.active_days if d not in DAYS]
    if bad_days:
        raise SuperfanError(f"{path}: active_days has {bad_days}; use {list(DAYS)}")
    if cfg.active_hours is not None:
        _parse_hours(cfg.active_hours)
    return cfg


def _parse_hours(spec: str) -> tuple[int, int]:
    """'08:00-18:00' -> minutes since midnight (480, 1080)."""
    m = re.fullmatch(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", spec)
    if not m:
        raise SuperfanError(f"active_hours {spec!r} is not HH:MM-HH:MM")
    h1, m1, h2, m2 = map(int, m.groups())
    return h1 * 60 + m1, h2 * 60 + m2


def is_active(cfg: Config, now: datetime) -> bool:
    if DAYS[now.weekday()] not in cfg.active_days:
        return False
    if cfg.active_hours is None:
        return True
    start, end = _parse_hours(cfg.active_hours)
    minute = now.hour * 60 + now.minute
    return start <= minute < end


# --- files ---------------------------------------------------------------------------


def read_ledger(d: Path) -> list[dict]:
    path = d / "ledger.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def read_finding(path: Path) -> dict:
    """Parse the frontmatter of an inbox/closed finding file."""
    text = path.read_text(encoding="utf-8")
    meta: dict = {"id": path.stem}
    if text.startswith("---\n"):
        head = text[4:].split("\n---\n", 1)[0]
        for line in head.splitlines():
            key, _, value = line.partition(": ")
            meta[key] = value
    return meta


def findings_in(d: Path, sub: str) -> list[dict]:
    folder = d / sub
    if not folder.exists():
        return []
    return [read_finding(p) for p in sorted(folder.glob("*.md"))]


def append_digest(d: Path, now: datetime, text: str) -> None:
    folder = d / "digest"
    folder.mkdir(exist_ok=True)
    with (folder / f"{now:%Y-%m-%d}.md").open("a", encoding="utf-8") as fh:
        fh.write(text.rstrip("\n") + "\n")


def load_state(d: Path) -> dict:
    path = d / "state.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"failures": 0}


def save_state(d: Path, state: dict) -> None:
    (d / "state.json").write_text(json.dumps(state), encoding="utf-8")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "finding"


# --- prompt ----------------------------------------------------------------------------


def build_prompt(cfg: Config, now: datetime) -> str:
    d = component_dir(cfg.component)
    parts = [
        WATCH_PROMPT.read_text(encoding="utf-8").replace("{component}", cfg.component),
        f"## Now\n\n{now:%Y-%m-%d %H:%M %A} (local time)",
        "## Charter\n\n" + (d / "charter.md").read_text(encoding="utf-8"),
        "## Baselines\n\n" + _read_or(d / "baselines.md", "No baselines yet."),
        "## Open findings (no verdict yet; reuse these fingerprints, do not re-raise them)\n\n"
        + _bullets(f"`{f.get('fingerprint')}` {f.get('title')}" for f in findings_in(d, "inbox")),
        "## Recent verdicts from your human (do not raise these again)\n\n"
        + _bullets(
            f"`{v['fingerprint']}` {v.get('title', '')} -> {v['verdict']}"
            + (f": {v['note']}" if v.get("note") else "")
            for v in read_ledger(d)[-RECENT_VERDICTS:]
        ),
    ]
    if cfg.neighbors:
        parts.append("## What neighboring superfans saw in the last 24h\n\n" + _neighbors(cfg, now))
    return "\n\n".join(parts) + "\n"


def _read_or(path: Path, fallback: str) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else fallback


def _bullets(lines) -> str:
    items = [f"- {line}" for line in lines]
    return "\n".join(items) if items else "None."


def _neighbors(cfg: Config, now: datetime) -> str:
    cutoff = now - timedelta(hours=NEIGHBOR_HOURS)
    lines = []
    for name in cfg.neighbors:
        nd = component_dir(name)
        for f in findings_in(nd, "inbox") + findings_in(nd, "closed"):
            seen = f.get("last_seen") or f.get("created", "")
            if seen and datetime.fromisoformat(seen) >= cutoff:
                lines.append(f"{name}: [{f.get('severity')}] {f.get('title')} (seen {seen})")
    return _bullets(lines)


# --- run -------------------------------------------------------------------------------


def claude_argv(cfg: Config) -> list[str]:
    argv = [
        "claude",
        "-p",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(REPORT_SCHEMA),
        # No built-in tools: no Bash, no file writes, no web. Only the allowlisted MCP reads.
        "--tools",
        "",
        "--allowedTools",
        *cfg.allowed_tools,
        "--permission-mode",
        "dontAsk",
        "--model",
        cfg.model,
        "--max-budget-usd",
        str(cfg.max_budget_usd),
        "--no-session-persistence",
    ]
    if cfg.mcp_config:
        argv += ["--mcp-config", str(Path(cfg.mcp_config).expanduser()), "--strict-mcp-config"]
    return argv


def parse_report(stdout: str) -> tuple[dict, dict]:
    """Return (report, envelope) from ``claude -p --output-format json`` stdout."""
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RunFailed(f"output is not JSON: {exc}") from exc
    if envelope.get("is_error"):
        raise RunFailed(f"claude reported an error: {envelope.get('result')!r}")
    report = envelope.get("structured_output")
    if report is None:
        try:
            report = json.loads(envelope.get("result") or "")
        except json.JSONDecodeError as exc:
            raise RunFailed("no structured_output and result is not JSON") from exc
    if not isinstance(report, dict) or not {"status", "summary", "findings"} <= set(report):
        raise RunFailed(f"report is missing required keys: {report!r}")
    return report, envelope


Runner = Callable[..., subprocess.CompletedProcess]


def run(cfg: Config, now: datetime, runner: Runner = subprocess.run) -> int:
    d = component_dir(cfg.component)
    if not is_active(cfg, now):
        print(f"{cfg.component}: outside active hours, skipping")
        return 0
    runs = d / "runs"
    runs.mkdir(exist_ok=True)
    stamp = f"{now:%Y%m%dT%H%M%S}"
    try:
        proc = runner(
            claude_argv(cfg),
            input=build_prompt(cfg, now),
            capture_output=True,
            text=True,
            cwd=d,
            timeout=cfg.timeout_seconds,
        )
        (runs / f"{stamp}.json").write_text(proc.stdout or "", encoding="utf-8")
        if proc.returncode != 0 and not proc.stdout:
            raise RunFailed(f"claude exited {proc.returncode}: {proc.stderr.strip()[:500]}")
        report, envelope = parse_report(proc.stdout)
        if report["status"] == "blind":
            # The model ran but could not see its signals: as useless as a crash, and quieter.
            (runs / f"{stamp}.json").write_text(proc.stdout, encoding="utf-8")
            raise RunFailed(f"blind: {report['summary'][:300]}")
    except (RunFailed, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return _record_failure(cfg, d, now, exc)

    save_state(d, {"failures": 0})
    paged, digested, repeats = record_findings(cfg, d, now, report["findings"])
    if report.get("baselines"):
        base = d / "baselines.md"
        if base.exists():
            shutil.copy(base, d / "baselines.md.bak")
        base.write_text(report["baselines"].rstrip("\n") + "\n", encoding="utf-8")
    denials = envelope.get("permission_denials") or []
    cost = envelope.get("total_cost_usd") or 0.0
    line = (
        f"- {now:%H:%M} {report['status']} ${cost:.3f}: {report['summary']}"
        f" (paged {paged}, digest {digested}, repeats {repeats}"
        + (f", {len(denials)} tool calls denied" if denials else "")
        + ")"
    )
    append_digest(d, now, line)
    print(line)
    return 0


def _record_failure(cfg: Config, d: Path, now: datetime, exc: Exception) -> int:
    state = load_state(d)
    state["failures"] = state.get("failures", 0) + 1
    save_state(d, state)
    append_digest(d, now, f"- {now:%H:%M} FAILED: {exc}")
    print(f"{cfg.component}: run failed: {exc}", file=sys.stderr)
    if state["failures"] == cfg.failure_alert_after:
        notify(
            cfg,
            f"superfan {cfg.component} is blind",
            f"{state['failures']} runs failed in a row. Last: {str(exc)[:120]}",
            None,
        )
    return 1


def suppressed(cfg: Config, ledger: list[dict], fingerprint: str, now: datetime) -> bool:
    """True when the human already said this fingerprint is known, or noise recently."""
    window = timedelta(days=cfg.suppress_noise_days)
    for v in ledger:
        if v["fingerprint"] != fingerprint:
            continue
        if v["verdict"] == "known":
            return True
        if v["verdict"] == "noise" and now - datetime.fromisoformat(v["at"]) < window:
            return True
    return False


def record_findings(
    cfg: Config, d: Path, now: datetime, findings: list[dict]
) -> tuple[int, int, int]:
    inbox = d / "inbox"
    inbox.mkdir(exist_ok=True)
    ledger = read_ledger(d)
    open_by_fp = {f.get("fingerprint"): f for f in findings_in(d, "inbox")}
    paged = digested = repeats = 0
    for f in findings:
        # same_as is the model's explicit claim that this is an anomaly already on record;
        # it wins over a freshly worded fingerprint, which drifts between passes.
        fp = slug(f.get("same_as") or f["fingerprint"])  # slug is idempotent
        if suppressed(cfg, ledger, fp, now):
            continue
        if fp in open_by_fp:
            _bump_seen(inbox / f"{open_by_fp[fp]['id']}.md", now)
            repeats += 1
            continue
        finding_id = f"{now:%Y%m%dT%H%M%S}-{slug(fp)}"
        (inbox / f"{finding_id}.md").write_text(render_finding(fp, f, now), encoding="utf-8")
        open_by_fp[fp] = {"id": finding_id, "fingerprint": fp}
        if f["severity"] == "page":
            body = (f["evidence"] or [f["title"]])[0]
            notify(cfg, f"{cfg.component}: {f['title']}", body, finding_id)
            paged += 1
        else:
            append_digest(d, now, f"  - [{finding_id}] {f['title']}")
            digested += 1
    return paged, digested, repeats


def render_finding(fp: str, f: dict, now: datetime) -> str:
    title = " ".join(f["title"].split())  # one line, so the frontmatter stays parseable

    def section(title: str, items: list[str]) -> str:
        return f"## {title}\n\n" + "\n".join(f"- {i}" for i in items) + "\n\n" if items else ""

    return (
        "---\n"
        f"fingerprint: {fp}\n"
        f"severity: {f['severity']}\n"
        f"title: {title}\n"
        f"created: {now.isoformat(timespec='seconds')}\n"
        f"last_seen: {now.isoformat(timespec='seconds')}\n"
        "seen: 1\n"
        "---\n\n"
        f"# {title}\n\n"
        + section("Evidence", f["evidence"])
        + (f"## Suspected cause\n\n{f['suspected_cause']}\n\n" if f.get("suspected_cause") else "")
        + section("Next checks", f.get("next_checks") or [])
    )


def _bump_seen(path: Path, now: datetime) -> None:
    text = path.read_text(encoding="utf-8")
    stamp = now.isoformat(timespec="seconds")
    text = re.sub(r"^last_seen: .*$", f"last_seen: {stamp}", text, count=1, flags=re.M)
    text = re.sub(
        r"^seen: (\d+)$", lambda m: f"seen: {int(m.group(1)) + 1}", text, count=1, flags=re.M
    )
    path.write_text(text, encoding="utf-8")


# --- verdicts and stats ----------------------------------------------------------------


def verdict(component: str, finding_id: str, value: str, note: str, now: datetime) -> Path:
    if value not in VERDICTS:
        raise SuperfanError(f"verdict must be one of {VERDICTS}, not {value!r}")
    d = component_dir(component)
    src = d / "inbox" / f"{finding_id}.md"
    if not src.exists():
        raise SuperfanError(f"no open finding {finding_id!r} in {d / 'inbox'}")
    meta = read_finding(src)
    entry = {
        "id": finding_id,
        "fingerprint": meta.get("fingerprint", ""),
        "severity": meta.get("severity", ""),
        "title": meta.get("title", ""),
        "verdict": value,
        "note": note,
        "at": now.isoformat(timespec="seconds"),
    }
    with (d / "ledger.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    closed = d / "closed"
    closed.mkdir(exist_ok=True)
    dest = closed / src.name
    src.rename(dest)
    return dest


def stats(component: str) -> dict:
    d = component_dir(component)
    runs = sorted((d / "runs").glob("*.json")) if (d / "runs").exists() else []
    cost = 0.0
    failed = 0
    for path in runs:
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            cost += envelope.get("total_cost_usd") or 0.0
            failed += bool(envelope.get("is_error"))
        except json.JSONDecodeError:
            failed += 1
    ledger = read_ledger(d)
    by_verdict = {v: sum(1 for e in ledger if e["verdict"] == v) for v in VERDICTS}
    pages = [e for e in ledger if e.get("severity") == "page"]
    page_noise = sum(1 for e in pages if e["verdict"] != "real")
    return {
        "runs": len(runs),
        "failed_runs": failed,
        "cost_usd": round(cost, 4),
        "open": len(findings_in(d, "inbox")),
        "verdicts": by_verdict,
        "page_precision": round(1 - page_noise / len(pages), 3) if pages else None,
    }


# --- notification ----------------------------------------------------------------------


def _open_command(component: str, finding_id: str) -> str:
    return shlex.join(
        [sys.executable, str(Path(__file__).resolve()), "open", component, finding_id]
    )


def _notify_terminal_notifier(cfg: Config, title: str, body: str, finding_id: str | None):
    argv = ["terminal-notifier", "-title", title, "-message", body, "-group", cfg.component]
    if finding_id:
        argv += ["-execute", _open_command(cfg.component, finding_id)]
    subprocess.run(argv, check=False)


def _notify_osascript(cfg: Config, title: str, body: str, finding_id: str | None):
    script = f"display notification {json.dumps(body)} with title {json.dumps(title)}"
    subprocess.run(["osascript", "-e", script], check=False)


def _notify_stdout(cfg: Config, title: str, body: str, finding_id: str | None):
    print(f"NOTIFY {title}: {body}" + (f" [{finding_id}]" if finding_id else ""))


def _notify_command(cfg: Config, title: str, body: str, finding_id: str | None):
    """Any transport you can reach from a shell, e.g. a Teams Workflows webhook via curl."""
    env = {
        **os.environ,
        "SUPERFAN_COMPONENT": cfg.component,
        "SUPERFAN_TITLE": title,
        "SUPERFAN_BODY": body,
        "SUPERFAN_FINDING": finding_id or "",
    }
    subprocess.run(cfg.notify_command, shell=True, env=env, check=False)


NOTIFIERS = {
    "terminal-notifier": _notify_terminal_notifier,
    "osascript": _notify_osascript,
    "stdout": _notify_stdout,
    "command": _notify_command,
}


def notify(cfg: Config, title: str, body: str, finding_id: str | None) -> None:
    NOTIFIERS[cfg.notify](cfg, title, body, finding_id)


def open_triage(component: str, finding_id: str) -> None:
    """Open Terminal running an interactive triage session on one finding."""
    d = component_dir(component)
    cmd = f"cd {shlex.quote(str(d))} && claude {shlex.quote(f'/superfan:triage {component} {finding_id}')}"
    script = f'tell application "Terminal"\nactivate\ndo script {json.dumps(cmd)}\nend tell'
    subprocess.run(["osascript", "-e", script], check=False)


# --- init and launchd ------------------------------------------------------------------


def init(component: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", component) or component == "bin":
        raise SuperfanError(f"component name {component!r}: use lowercase letters, digits, -")
    d = component_dir(component)
    d.mkdir(parents=True, exist_ok=True)
    for name in ("superfan.toml", "charter.md", "baselines.md"):
        dest = d / name
        if not dest.exists():
            text = (TEMPLATES / name).read_text(encoding="utf-8")
            dest.write_text(text.replace("{component}", component), encoding="utf-8")
    for sub in ("inbox", "closed", "digest", "runs"):
        (d / sub).mkdir(exist_ok=True)
    return d


def plist_path(component: str) -> Path:
    return LAUNCH_AGENTS / f"com.superfan.{component}.plist"


def render_plist(cfg: Config, path_env: str, script: Path) -> str:
    d = component_dir(cfg.component)
    args = [sys.executable, str(script), "run", cfg.component]
    arg_xml = "\n".join(f"    <string>{_xml(a)}</string>" for a in args)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.superfan.{_xml(cfg.component)}</string>
  <key>ProgramArguments</key>
  <array>
{arg_xml}
  </array>
  <key>StartInterval</key>
  <integer>{cfg.cadence_minutes * 60}</integer>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>{_xml(path_env)}</string>
    <key>SUPERFAN_HOME</key>
    <string>{_xml(str(home()))}</string>
  </dict>
  <key>StandardOutPath</key>
  <string>{_xml(str(d / "launchd.out.log"))}</string>
  <key>StandardErrorPath</key>
  <string>{_xml(str(d / "launchd.err.log"))}</string>
</dict>
</plist>
"""


def _xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def install(component: str, load: bool, runner: Runner = subprocess.run) -> Path:
    cfg = load_config(component)
    # The plugin cache directory changes on every plugin update, so the agent runs a copy
    # that install refreshes. Re-run install after updating the plugin.
    bin_dir = home() / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "superfan.py"
    shutil.copy(Path(__file__).resolve(), script)
    shutil.copy(WATCH_PROMPT, bin_dir / WATCH_PROMPT.name)
    path = plist_path(component)
    path.parent.mkdir(parents=True, exist_ok=True)
    # launchd starts jobs with a bare PATH; capture the one that can find claude and the
    # notifier now, while we are in the user's shell.
    path.write_text(render_plist(cfg, os.environ.get("PATH", ""), script), encoding="utf-8")
    if load:
        domain = f"gui/{os.getuid()}"
        runner(["launchctl", "bootout", domain, str(path)], check=False, capture_output=True)
        runner(["launchctl", "bootstrap", domain, str(path)], check=True)
    return path


def uninstall(component: str, runner: Runner = subprocess.run) -> Path:
    path = plist_path(component)
    runner(["launchctl", "bootout", f"gui/{os.getuid()}", str(path)], check=False)
    path.unlink(missing_ok=True)
    return path


# --- cli -------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="superfan", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("init", "run", "stats", "uninstall", "notify-test"):
        sub.add_parser(name).add_argument("component")
    p = sub.add_parser("verdict")
    p.add_argument("component")
    p.add_argument("finding_id")
    p.add_argument("verdict", choices=VERDICTS)
    p.add_argument("--note", default="")
    p = sub.add_parser("install")
    p.add_argument("component")
    p.add_argument("--load", action="store_true")
    p = sub.add_parser("open")
    p.add_argument("component")
    p.add_argument("finding_id")
    args = parser.parse_args(argv)
    now = datetime.now()

    try:
        if args.cmd == "init":
            print(init(args.component))
        elif args.cmd == "run":
            return run(load_config(args.component), now)
        elif args.cmd == "verdict":
            print(verdict(args.component, args.finding_id, args.verdict, args.note, now))
        elif args.cmd == "stats":
            print(json.dumps(stats(args.component), indent=2))
        elif args.cmd == "install":
            print(install(args.component, args.load))
        elif args.cmd == "uninstall":
            print(uninstall(args.component))
        elif args.cmd == "notify-test":
            notify(load_config(args.component), f"superfan {args.component}", "test", None)
        elif args.cmd == "open":
            open_triage(args.component, args.finding_id)
    except SuperfanError as exc:
        print(f"superfan: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
