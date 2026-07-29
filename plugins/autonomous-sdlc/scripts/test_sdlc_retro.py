# ABOUTME: Tests for sdlc_retro.py — the run-ledger digest and retro marker CLI.
# ABOUTME: Covers windowing by marker, per-version stats, and worst-run surfacing.
"""Run from this directory: `python3 -m pytest test_sdlc_retro.py` (or plain
`python3 test_sdlc_retro.py` for the bundled fallback runner)."""

import importlib.util
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "sdlc_retro", Path(__file__).with_name("sdlc_retro.py")
)
sdlc_retro = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sdlc_retro)


def _record(score, outcome="DONE", version="2.4.0", reason="pr", **extra):
    return {
        "at": "2026-07-08T00:00:00+00:00",
        "repo": "demo",
        "feature": "f",
        "plugin_version": version,
        "terminal_reason": reason,
        "outcome": outcome,
        "score": score,
        "rework": {"verify_bounces": 1, "review_roundtrips": 0,
                   "replans": 0, "repairs": 0},
        "attempts_exceeded": 0,
        "archive": "/tmp/x",
        **extra,
    }


def _write_ledger(root: Path, records):
    root.mkdir(parents=True, exist_ok=True)
    with (root / "runs.jsonl").open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _digest(root, **ns):
    os.environ["SDLC_RUNS_DIR"] = str(root)
    try:
        out = io.StringIO()
        args = sdlc_retro.argparse.Namespace(
            all=ns.get("all", False), worst=ns.get("worst", 3)
        )
        with redirect_stdout(out):
            sdlc_retro.cmd_digest(args)
        return json.loads(out.getvalue())
    finally:
        del os.environ["SDLC_RUNS_DIR"]


def _mark(root, note="n"):
    os.environ["SDLC_RUNS_DIR"] = str(root)
    try:
        out = io.StringIO()
        with redirect_stdout(out):
            sdlc_retro.cmd_mark(sdlc_retro.argparse.Namespace(note=note))
    finally:
        del os.environ["SDLC_RUNS_DIR"]


def test_digest_empty_ledger(tmp_path):
    digest = _digest(tmp_path)
    assert digest["runs"] == 0
    assert digest["previous_retro"] is None


def test_digest_aggregates_and_surfaces_worst(tmp_path):
    _write_ledger(
        tmp_path,
        [
            _record(0.9),
            _record(0.2, outcome="BLOCKED", reason="budget: max_iterations=50"),
            _record(0.7),
        ],
    )
    digest = _digest(tmp_path, worst=1)
    assert digest["runs"] == 3
    assert digest["outcomes"] == {"DONE": 2, "BLOCKED": 1}
    assert digest["blocked_reasons"] == {"budget: max_iterations=50": 1}
    assert digest["rework_totals"]["verify_bounces"] == 3
    assert len(digest["worst_runs"]) == 1
    assert digest["worst_runs"][0]["score"] == 0.2
    assert digest["score"]["n"] == 3
    assert digest["score"]["comparable"] is False  # below MIN_WINDOW_N


def test_mark_windows_the_next_digest(tmp_path):
    _write_ledger(tmp_path, [_record(0.5), _record(0.6)])
    _mark(tmp_path, note="first retro")
    # Two more runs arrive after the retro.
    with (tmp_path / "runs.jsonl").open("a") as f:
        f.write(json.dumps(_record(0.8)) + "\n")
        f.write(json.dumps(_record(0.9)) + "\n")

    digest = _digest(tmp_path)
    assert digest["since_last_retro"] is True
    assert digest["runs"] == 2  # only post-marker runs
    assert digest["ledger_total"] == 4
    assert digest["previous_retro"]["note"] == "first retro"
    # --all ignores the marker.
    assert _digest(tmp_path, all=True)["runs"] == 4


def test_version_windows_span_whole_ledger(tmp_path):
    # Grading a previous retro needs pre-change runs even when the marker
    # window excludes them: by_plugin_version must cover the whole ledger.
    records = [_record(0.4, version="2.3.1") for _ in range(5)]
    records += [_record(0.8, version="2.4.0") for _ in range(5)]
    _write_ledger(tmp_path, records)
    _mark(tmp_path)
    with (tmp_path / "runs.jsonl").open("a") as f:
        f.write(json.dumps(_record(0.9, version="2.4.0")) + "\n")

    digest = _digest(tmp_path)
    versions = digest["by_plugin_version"]
    assert versions["2.3.1"]["n"] == 5
    assert versions["2.4.0"]["n"] == 6
    assert versions["2.3.1"]["comparable"] and versions["2.4.0"]["comparable"]
    assert versions["2.4.0"]["pessimistic"] > versions["2.3.1"]["pessimistic"]


if __name__ == "__main__":
    # Minimal fallback runner so the suite works without pytest installed.
    import tempfile
    import traceback

    tests = [
        test_digest_empty_ledger,
        test_digest_aggregates_and_surfaces_worst,
        test_mark_windows_the_next_digest,
        test_version_windows_span_whole_ledger,
    ]
    failures = 0
    for t in tests:
        with tempfile.TemporaryDirectory() as d:
            try:
                t(Path(d))
                print(f"PASS {t.__name__}")
            except Exception:
                failures += 1
                print(f"FAIL {t.__name__}")
                traceback.print_exc()
    raise SystemExit(1 if failures else 0)
