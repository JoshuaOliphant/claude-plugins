"""Direct HTTP transport (``delivery.transport = "webhook"``)."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request

from ..domain.models import Batch
from ..services.retry import TransientError


class WebhookError(RuntimeError):
    pass


class WebhookTransport:
    name = "webhook"

    def __init__(self, service: str, timeout: float, verify_tls: bool = True,
                 opener=urllib.request.urlopen):
        self.service = service
        self.timeout = timeout
        self.verify_tls = verify_tls
        self._open = opener

    def _context(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        if not self.verify_tls:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def request(self, batch: Batch) -> urllib.request.Request:
        body = json.dumps(batch.envelope(self.service)).encode("utf-8")
        return urllib.request.Request(
            batch.endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"{self.service}/relaydesk",
                "X-Relay-Batch": str(batch.number),
            },
        )

    def deliver(self, batch: Batch) -> str:
        req = self.request(batch)
        try:
            with self._open(req, timeout=self.timeout, context=self._context()) as resp:
                status = resp.status
        except urllib.error.HTTPError as exc:
            if exc.code >= 500 or exc.code == 429:
                raise TransientError(f"HTTP {exc.code}") from None
            raise WebhookError(f"HTTP {exc.code} for batch {batch.number}") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            raise TransientError(str(exc)) from None
        return f"HTTP {status}"
