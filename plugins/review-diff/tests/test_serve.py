import json
import subprocess
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager

import pytest

import serve
from collect import NotAGitRepo
from serve import render_html, start_server, validate_review


def test_render_html_embeds_data():
    data = {"repo": "demo", "files": [], "has_changes": False}
    html = render_html(data)
    assert "/*__EMBEDDED_DATA__*/" not in html
    assert "const EMBEDDED_DATA =" in html
    assert '"repo": "demo"' in html or '"repo":"demo"' in html


def test_render_html_escapes_script_breakout():
    data = {"repo": "x", "files": [], "has_changes": False, "evil": "</script><b>"}
    html = render_html(data)
    # The literal breakout sequence must NOT appear verbatim...
    assert "</script><b>" not in html
    # ...it must be escaped to \uXXXX forms instead.
    assert "\\u003c/script\\u003e\\u003cb\\u003e" in html


def test_validate_review_defaults_summary():
    out = validate_review({"comments": []})
    assert out == {"comments": [], "summary": ""}


def test_validate_review_keeps_fields():
    payload = {
        "summary": "ok",
        "comments": [{"file": "a", "line": 1, "side": "new", "code": "x", "body": "b"}],
    }
    assert validate_review(payload) == payload


def test_validate_review_rejects_non_dict():
    with pytest.raises(ValueError):
        validate_review([1, 2, 3])


def test_validate_review_rejects_missing_comments():
    with pytest.raises(ValueError):
        validate_review({"summary": "no comments key"})


_DIFF = {"repo": "demo", "files": [], "has_changes": True}


@contextmanager
def spawn_server(review_path):
    """Run a ReviewHandler server on a free port for the duration of the block."""
    server = start_server(_DIFF, review_path, 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def running_server(tmp_path):
    review_path = tmp_path / "review.json"
    with spawn_server(review_path) as base:
        yield base, review_path


def test_get_index_returns_html(running_server):
    base, _ = running_server
    body = urllib.request.urlopen(base + "/").read().decode()
    assert "const EMBEDDED_DATA =" in body


def test_post_review_writes_file(running_server):
    base, review_path = running_server
    payload = json.dumps({"summary": "s", "comments": []}).encode()
    req = urllib.request.Request(
        base + "/api/review", data=payload, headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req)
    assert resp.status == 200
    saved = json.loads(review_path.read_text())
    assert saved == {"summary": "s", "comments": []}


def test_get_review_roundtrip(running_server):
    base, review_path = running_server
    review_path.write_text(json.dumps({"summary": "hi", "comments": []}))
    body = urllib.request.urlopen(base + "/api/review").read().decode()
    assert json.loads(body)["summary"] == "hi"


def test_get_review_empty_when_missing(running_server):
    base, _ = running_server
    body = urllib.request.urlopen(base + "/api/review").read().decode()
    assert json.loads(body) == {}


def test_review_roundtrip_through_server(running_server):
    # The real user loop: POST a review to the running server, then GET it back
    # from the SAME server and confirm it matches. Exercises the write and read
    # halves against each other, not just against the filesystem.
    base, _ = running_server
    payload = {
        "summary": "looks good",
        "comments": [{"file": "a.py", "line": 3, "side": "new", "body": "nit"}],
    }
    req = urllib.request.Request(
        base + "/api/review",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    assert urllib.request.urlopen(req).status == 200
    got = json.loads(urllib.request.urlopen(base + "/api/review").read().decode())
    assert got["summary"] == "looks good"
    assert got["comments"] == payload["comments"]


def test_post_review_returns_500_on_write_failure(tmp_path):
    # If review.json can't be written (here: its parent dir doesn't exist) the
    # server must answer 500 so the client can fall back to a local download,
    # rather than crashing or silently losing the review.
    bad_path = tmp_path / "missing-dir" / "review.json"
    with spawn_server(bad_path) as base:
        req = urllib.request.Request(
            base + "/api/review",
            data=json.dumps({"summary": "s", "comments": []}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req)
        assert exc.value.code == 500


def test_post_invalid_json_returns_400(running_server):
    base, _ = running_server
    req = urllib.request.Request(
        base + "/api/review", data=b"not json", headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 400


def test_unknown_get_returns_404(running_server):
    base, _ = running_server
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(base + "/nope")
    assert exc.value.code == 404


def test_unknown_post_returns_404(running_server):
    base, _ = running_server
    req = urllib.request.Request(
        base + "/nope", data=b"{}", headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 404


def test_start_server_falls_back_on_busy_port(tmp_path):
    # Binding to an already-listening port raises OSError -> fall back to a free port.
    first = start_server(_DIFF, tmp_path / "r1.json", 0)
    busy = first.server_address[1]
    try:
        second = start_server(_DIFF, tmp_path / "r2.json", busy)
        try:
            assert second.server_address[1] != busy
        finally:
            second.server_close()
    finally:
        first.server_close()


def test_kill_port_sends_sigterm(monkeypatch):
    calls = {"killed": []}

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="123\n456\n", stderr="")

    monkeypatch.setattr(serve.subprocess, "run", fake_run)
    monkeypatch.setattr(serve.os, "kill", lambda pid, sig: calls["killed"].append(pid))
    monkeypatch.setattr(serve.time, "sleep", lambda s: None)
    serve._kill_port(9999)
    assert calls["killed"] == [123, 456]


def test_kill_port_handles_missing_lsof(monkeypatch):
    def fake_run(args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(serve.subprocess, "run", fake_run)
    serve._kill_port(9999)  # must not raise


def test_kill_port_handles_dead_pid(monkeypatch):
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="123\n", stderr="")

    def boom(pid, sig):
        raise ProcessLookupError

    monkeypatch.setattr(serve.subprocess, "run", fake_run)
    monkeypatch.setattr(serve.os, "kill", boom)
    monkeypatch.setattr(serve.time, "sleep", lambda s: None)
    serve._kill_port(9999)  # must not raise


def test_main_not_a_repo(monkeypatch, capsys):
    monkeypatch.setattr(
        serve, "collect_diff", lambda path: (_ for _ in ()).throw(NotAGitRepo(path))
    )
    rc = serve.main(["--path", "/tmp/nope"])
    assert rc == 1
    assert "not a git repository" in capsys.readouterr().err


def test_main_no_changes(monkeypatch, capsys):
    # Clean working tree and no resolvable base -> nothing to review.
    monkeypatch.setattr(
        serve,
        "collect_diff",
        lambda path, base=None: {"repo": "x", "files": [], "has_changes": False},
    )
    monkeypatch.setattr(serve, "resolve_base", lambda path: None)
    rc = serve.main(["--path", "."])
    assert rc == 0
    assert "NO_CHANGES" in capsys.readouterr().out


def test_main_static_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(
        serve, "collect_diff", lambda path: {"repo": "x", "files": [], "has_changes": True}
    )
    out = tmp_path / "out.html"
    rc = serve.main(["--path", ".", "--static", str(out)])
    assert rc == 0
    assert "const EMBEDDED_DATA =" in out.read_text()


def test_main_serves_until_interrupt(monkeypatch, tmp_path):
    events = {"opened": None, "closed": False}

    class FakeServer:
        server_address = ("127.0.0.1", 4321)

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            events["closed"] = True

    monkeypatch.setattr(
        serve, "collect_diff", lambda path: {"repo": "x", "files": [], "has_changes": True}
    )
    monkeypatch.setattr(serve, "_kill_port", lambda port: None)
    monkeypatch.setattr(serve, "start_server", lambda data, rp, port: FakeServer())
    monkeypatch.setattr(serve.webbrowser, "open", lambda url: events.__setitem__("opened", url))
    rc = serve.main(["--path", str(tmp_path), "--port", "4321"])
    assert rc == 0
    assert events["opened"] == "http://localhost:4321"
    assert events["closed"] is True


def test_main_no_browser_flag(monkeypatch, tmp_path):
    opened = {"called": False}

    class FakeServer:
        server_address = ("127.0.0.1", 4322)

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            pass

    monkeypatch.setattr(
        serve, "collect_diff", lambda path: {"repo": "x", "files": [], "has_changes": True}
    )
    monkeypatch.setattr(serve, "_kill_port", lambda port: None)
    monkeypatch.setattr(serve, "start_server", lambda data, rp, port: FakeServer())
    monkeypatch.setattr(serve.webbrowser, "open", lambda url: opened.__setitem__("called", True))
    serve.main(["--path", str(tmp_path), "--no-browser"])
    assert opened["called"] is False


class _InterruptServer:
    server_address = ("127.0.0.1", 4330)

    def serve_forever(self):
        raise KeyboardInterrupt

    def server_close(self):
        pass


def test_main_explicit_base(monkeypatch, tmp_path, capsys):
    seen = []

    def fake_collect(path, base=None):
        seen.append(base)
        return {"repo": "x", "files": [{"path": "a"}], "has_changes": True}

    monkeypatch.setattr(serve, "collect_diff", fake_collect)
    monkeypatch.setattr(serve, "_kill_port", lambda port: None)
    monkeypatch.setattr(serve, "start_server", lambda data, rp, port: _InterruptServer())
    monkeypatch.setattr(serve.webbrowser, "open", lambda url: None)
    serve.main(["--path", str(tmp_path), "--base", "origin/main", "--no-browser"])
    assert seen == ["origin/main"]
    assert "Mode: branch vs origin/main" in capsys.readouterr().out


def test_main_auto_fallback_to_branch(monkeypatch, tmp_path, capsys):
    def fake_collect(path, base=None):
        # Working tree clean; the committed branch has changes vs its base.
        if base is None:
            return {"repo": "x", "files": [], "has_changes": False}
        return {"repo": "x", "files": [{"path": "a"}], "has_changes": True}

    monkeypatch.setattr(serve, "collect_diff", fake_collect)
    monkeypatch.setattr(serve, "resolve_base", lambda path: "origin/main")
    monkeypatch.setattr(serve, "_kill_port", lambda port: None)
    monkeypatch.setattr(serve, "start_server", lambda data, rp, port: _InterruptServer())
    monkeypatch.setattr(serve.webbrowser, "open", lambda url: None)
    serve.main(["--path", str(tmp_path), "--no-browser"])
    assert "Mode: branch vs origin/main" in capsys.readouterr().out


def test_main_no_changes_even_after_fallback(monkeypatch, capsys):
    # Clean working tree AND an empty branch diff -> still nothing to review.
    monkeypatch.setattr(
        serve,
        "collect_diff",
        lambda path, base=None: {"repo": "x", "files": [], "has_changes": False},
    )
    monkeypatch.setattr(serve, "resolve_base", lambda path: "main")
    rc = serve.main(["--path", "."])
    assert rc == 0
    assert "NO_CHANGES" in capsys.readouterr().out


def test_main_git_error_surfaces(monkeypatch, capsys):
    # A git failure (e.g. a bad --base ref) must print a real error and exit
    # non-zero, never a silent NO_CHANGES.
    from collect import GitCommandError

    def fake_collect(path, base=None):
        raise GitCommandError(["diff", f"{base}...HEAD"], "fatal: bad revision")

    monkeypatch.setattr(serve, "collect_diff", fake_collect)
    rc = serve.main(["--path", ".", "--base", "nope"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "fatal: bad revision" in captured.err
    assert "NO_CHANGES" not in captured.out
