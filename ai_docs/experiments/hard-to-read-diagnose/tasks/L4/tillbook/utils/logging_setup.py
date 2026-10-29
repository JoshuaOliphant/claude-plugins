"""Logging configuration for the command line tools.

Log lines are read by the store operators on the server itself, so they are
stamped in the server's local time like every other system log there.
"""

from __future__ import annotations

import logging
import os
import sys
import time

_CONFIGURED = False

LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


class OperatorFormatter(logging.Formatter):
    """``2026-03-14 23:10:05 +0530 WARNING tillbook.storage: message``."""

    converter = time.localtime

    def formatTime(self, record, datefmt=None):  # noqa: N802 - logging API
        stamp = self.converter(record.created)
        return time.strftime("%Y-%m-%d %H:%M:%S %z", stamp)

    def format(self, record):
        record.asctime = self.formatTime(record)
        base = f"{record.asctime} {record.levelname:<7} {record.name}: {record.getMessage()}"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def configure(level: str | None = None) -> None:
    """Install the operator formatter on the ``tillbook`` logger once."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    name = (level or os.environ.get("TILLBOOK_LOG_LEVEL") or "warning").lower()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(OperatorFormatter())
    root = logging.getLogger("tillbook")
    root.addHandler(handler)
    root.setLevel(LEVELS.get(name, logging.WARNING))
    root.propagate = False
    _CONFIGURED = True
