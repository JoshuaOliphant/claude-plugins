"""Logging setup."""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False

FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure(level: str = "WARNING") -> None:
    """Configure the root freightdesk logger once per process."""
    global _CONFIGURED
    logger = logging.getLogger("freightdesk")
    numeric = getattr(logging, level.upper(), logging.WARNING)
    logger.setLevel(numeric)
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(handler)
    logger.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    if not name.startswith("freightdesk"):
        name = f"freightdesk.{name}"
    return logging.getLogger(name)
