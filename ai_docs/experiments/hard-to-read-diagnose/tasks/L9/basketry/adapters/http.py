"""Minimal WSGI shim exposing the summary API over HTTP.

    POST /summaries          body: order request JSON  -> summary JSON
    POST /summaries?format=text                        -> plain-text receipt
    GET  /health                                       -> {"status": "ok", ...}
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import parse_qs

from .. import api
from ..utils.validation import ValidationError

MAX_BODY_BYTES = 64 * 1024

StartResponse = Callable[[str, list[tuple[str, str]]], Any]


def _respond(start_response: StartResponse, status: str, body: str, content_type: str) -> list[bytes]:
    data = body.encode("utf-8")
    start_response(status, [("Content-Type", content_type), ("Content-Length", str(len(data)))])
    return [data]


def _json(start_response: StartResponse, status: str, payload: Any) -> list[bytes]:
    return _respond(start_response, status, json.dumps(payload, sort_keys=True), "application/json")


def _read_body(environ: dict[str, Any]) -> bytes:
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    if length > MAX_BODY_BYTES:
        raise ValidationError("request body too large")
    return environ["wsgi.input"].read(length) if length else b""


def application(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")
    query = parse_qs(environ.get("QUERY_STRING", ""))

    if path == "/health" and method == "GET":
        stats = api.get_service().stats
        return _json(start_response, "200 OK", {"status": "ok", "requests": stats.requests})

    if path != "/summaries":
        return _json(start_response, "404 Not Found", {"error": "not_found"})
    if method != "POST":
        return _json(start_response, "405 Method Not Allowed", {"error": "method_not_allowed"})

    try:
        payload = json.loads(_read_body(environ) or b"null")
        fmt = query.get("format", ["json"])[0]
        if fmt == "text":
            return _respond(start_response, "200 OK", api.summarize_text(payload), "text/plain; charset=utf-8")
        return _json(start_response, "200 OK", api.summarize(payload))
    except json.JSONDecodeError as exc:
        return _json(start_response, "400 Bad Request", {"error": "invalid_json", "message": str(exc)})
    except ValidationError as exc:
        return _json(start_response, "422 Unprocessable Entity", exc.to_dict())
    except LookupError as exc:
        return _json(start_response, "422 Unprocessable Entity", {"error": "lookup", "message": str(exc)})


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:  # pragma: no cover - manual use
    from wsgiref.simple_server import make_server

    with make_server(host, port, application) as server:
        print(f"basketry listening on http://{host}:{port}")
        server.serve_forever()
