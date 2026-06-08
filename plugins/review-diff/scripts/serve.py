"""Serve the diff review UI and capture submitted comments."""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import webbrowser
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from collect import GitCommandError, NotAGitRepo, collect_diff, resolve_base

_TEMPLATE = Path(__file__).parent / "viewer.html"
_PLACEHOLDER = "/*__EMBEDDED_DATA__*/"


def render_html(diff_data):
    template = _TEMPLATE.read_text()
    # Escape characters that could break out of the <script> context. The diff
    # data is arbitrary file content, so a reviewed file containing "</script>"
    # (or <, >, &) must not be able to inject markup. These \uXXXX forms parse
    # identically as JSON/JS, so the embedded value is unchanged.
    payload = (
        json.dumps(diff_data)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )
    return template.replace(_PLACEHOLDER, f"const EMBEDDED_DATA = {payload};")


def validate_review(data):
    if not isinstance(data, dict):
        raise ValueError("review must be a JSON object")
    if "comments" not in data or not isinstance(data["comments"], list):
        raise ValueError("review must contain a 'comments' array")
    data.setdefault("summary", "")
    return data


class ReviewHandler(BaseHTTPRequestHandler):
    def __init__(self, diff_data, review_path, *args, **kwargs):
        self.diff_data = diff_data
        self.review_path = review_path
        super().__init__(*args, **kwargs)

    def _send(self, code, content, ctype):
        body = content if isinstance(content, bytes) else content.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, render_html(self.diff_data), "text/html; charset=utf-8")
        elif self.path == "/api/review":
            data = self.review_path.read_bytes() if self.review_path.exists() else b"{}"
            self._send(200, data, "application/json")
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/review":
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length)
            try:
                data = validate_review(json.loads(body))
                self.review_path.write_text(json.dumps(data, indent=2) + "\n")
                self._send(200, b'{"ok":true}', "application/json")
            except (json.JSONDecodeError, ValueError) as exc:
                self._send(400, json.dumps({"error": str(exc)}).encode(), "application/json")
        else:
            self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def _kill_port(port):
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return
    for pid in result.stdout.split():
        try:
            os.kill(int(pid), signal.SIGTERM)
        except (ProcessLookupError, ValueError):
            pass
    if result.stdout.strip():
        time.sleep(0.5)


def start_server(diff_data, review_path, port):
    handler = partial(ReviewHandler, diff_data, review_path)
    try:
        return HTTPServer(("127.0.0.1", port), handler)
    except OSError:
        return HTTPServer(("127.0.0.1", 0), handler)


def _default_review_path(repo_path):
    # Keep review.json OUT of the user's repo so it never appears as an
    # untracked file in the next diff. Key it by repo root so concurrent
    # reviews of different repos don't collide.
    root = Path(repo_path).resolve()
    digest = hashlib.sha1(str(root).encode()).hexdigest()[:12]
    return Path(tempfile.gettempdir()) / "diff-review" / digest / "review.json"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve a diff review")
    parser.add_argument("--path", default=".", help="repo path")
    parser.add_argument("--port", type=int, default=3119)
    parser.add_argument("--review-file", default=None)
    parser.add_argument("--static", default=None)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--base",
        default=None,
        help="review a committed branch against this ref (e.g. origin/main) instead of the working tree",
    )
    args = parser.parse_args(argv)

    try:
        if args.base:
            diff_data = collect_diff(args.path, base=args.base)
            mode = f"branch vs {args.base}"
        else:
            diff_data = collect_diff(args.path)
            mode = "working tree"
            # Auto-fallback: if there are no uncommitted changes, review the
            # committed branch against its default base so "review this" works
            # on an already-committed/pushed branch too.
            if not diff_data["has_changes"]:
                base = resolve_base(args.path)
                if base is not None:
                    branch_data = collect_diff(args.path, base=base)
                    if branch_data["has_changes"]:
                        diff_data = branch_data
                        mode = f"branch vs {base}"
    except NotAGitRepo:
        print(f"Error: {args.path} is not a git repository", file=sys.stderr)
        return 1
    except GitCommandError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not diff_data["has_changes"]:
        print("NO_CHANGES")
        return 0

    print(f"Mode: {mode}", flush=True)

    if args.static:
        out = Path(args.static)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_html(diff_data))
        print(f"Static review written to: {out}")
        return 0

    review_path = Path(args.review_file) if args.review_file else _default_review_path(args.path)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    _kill_port(args.port)
    server = start_server(diff_data, review_path, args.port)
    port = server.server_address[1]
    url = f"http://localhost:{port}"
    # These three lines are the contract with the skill: it parses them rather
    # than reconstructing the path/port/pid itself. flush=True is essential —
    # the skill redirects stdout to a file, where it would otherwise be
    # block-buffered and never appear while serve_forever() blocks.
    print(f"Diff review server: {url}", flush=True)
    print(f"Review file: {review_path}", flush=True)
    print(f"PID: {os.getpid()}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover  # entry point, exercised via main()
    raise SystemExit(main())
