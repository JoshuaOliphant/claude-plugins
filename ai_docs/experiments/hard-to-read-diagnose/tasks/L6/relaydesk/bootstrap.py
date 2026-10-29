"""Process start-up: find the project, prime the environment, configure
logging and load settings."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from pathlib import Path

from .settings import Settings, load_settings
from .utils import envfile, paths

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def prime_environment(root: Path) -> dict[str, str]:
    return envfile.load(paths.env_files(root))


def configure_logging(level: str, verbose: int = 0) -> None:
    numeric = getattr(logging, level.upper(), logging.WARNING)
    if verbose:
        numeric = min(numeric, logging.INFO if verbose == 1 else logging.DEBUG)
    logging.basicConfig(level=numeric, format=_FORMAT, force=True)


def start(root: str | os.PathLike | None = None, config: str | None = None,
          overrides: Mapping[str, object] | None = None, verbose: int = 0) -> Settings:
    project = Path(root).resolve() if root else paths.find_project_root()
    prime_environment(project)
    settings = load_settings(project, config=config, overrides=overrides)
    configure_logging(str(settings.service.log_level), verbose)
    logging.getLogger("relaydesk").debug("project root %s, config %s",
                                         project, settings.config_path)
    return settings
