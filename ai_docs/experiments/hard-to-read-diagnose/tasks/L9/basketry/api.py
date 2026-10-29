"""Public, in-process API.

    >>> from basketry import api
    >>> api.summarize({"order_id": "W-1", "customer_id": "C-1002",
    ...                "lines": [{"sku": "MUG-STONE", "quantity": 2}]})["total_cents"]
    4499

The service and its loaded data are created on first use and reused for the
life of the process, which keeps per-request latency low for the HTTP shim
and the batch CLI alike.
"""

from __future__ import annotations

from typing import Any

from .adapters.codec import encode_summary
from .services.order_service import OrderService
from .utils.registry import get_renderer

_service: OrderService | None = None


def get_service() -> OrderService:
    global _service
    if _service is None:
        _service = OrderService.from_data_dir()
    return _service


def reset_service() -> None:
    """Drop the shared service so the next call reloads data from disk."""
    global _service
    _service = None


def summarize(payload: dict[str, Any]) -> dict[str, Any]:
    """Summarize one order request and return the JSON-ready summary."""
    return encode_summary(get_service().summarize(payload))


def summarize_text(payload: dict[str, Any]) -> str:
    """Summarize one order request as the plain-text customer receipt."""
    return render(payload, "text")


def render(payload: dict[str, Any], fmt: str = "text") -> str:
    from .adapters import render as _renderers  # noqa: F401  (registers renderers)

    return get_renderer(fmt)(get_service().summarize(payload))
