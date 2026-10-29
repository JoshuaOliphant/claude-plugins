"""Logging configuration for the command-line tools."""

from __future__ import annotations

import logging
import os
import sys

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
ENV_LEVEL = "LEDGERLY_LOG_LEVEL"

logging.getLogger("ledgerly").addHandler(logging.NullHandler())

_LEVELS = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}


def level_for(verbosity: int) -> int:
    env = os.environ.get(ENV_LEVEL)
    if env:
        named = logging.getLevelName(env.upper())
        if isinstance(named, int):
            return named
    return _LEVELS.get(min(verbosity, 2), logging.DEBUG)


def configure(verbosity: int = 0, stream=None) -> logging.Logger:
    """Attach a stderr handler to the ``ledgerly`` logger (idempotent)."""
    logger = logging.getLogger("ledgerly")
    logger.setLevel(level_for(verbosity))
    for handler in logger.handlers:
        if getattr(handler, "_ledgerly", False):
            handler.setLevel(logger.level)
            return logger
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(logger.level)
    handler._ledgerly = True
    logger.addHandler(handler)
    logger.propagate = False
    return logger
