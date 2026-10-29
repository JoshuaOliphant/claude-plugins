"""Logging setup for the CLI."""

from __future__ import annotations

import logging
import os
import sys

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_configured = False


def configure(verbosity: int = 0, stream=None) -> None:
    global _configured
    level = {0: logging.WARNING, 1: logging.INFO}.get(verbosity, logging.DEBUG)
    env = os.environ.get("LEDGERFLOW_LOG")
    if env:
        level = getattr(logging, env.upper(), level)
    root = logging.getLogger("ledgerflow")
    root.setLevel(level)
    if not _configured:
        handler = logging.StreamHandler(stream or sys.stderr)
        handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(handler)
        root.propagate = False
        _configured = True
