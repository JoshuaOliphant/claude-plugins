"""Discovery of plugin modules shipped inside a package directory.

Both the importer and exporter packages are "drop-in" directories: any
module placed there is imported at start-up and registers itself.
"""

from __future__ import annotations

import importlib
import logging
import os
from types import ModuleType

log = logging.getLogger(__name__)


def iter_module_names(directory: str):
    """Yield importable module names found directly in ``directory``.

    Private modules (leading underscore) and hidden files are skipped.
    """
    with os.scandir(directory) as entries:
        for entry in entries:
            name = entry.name
            if name.startswith(("_", ".")):
                continue
            if entry.is_file() and name.endswith(".py"):
                yield name[:-3]
            elif entry.is_dir() and os.path.isfile(os.path.join(entry.path, "__init__.py")):
                yield name


def import_submodules(package: str | ModuleType) -> list[str]:
    """Import every public submodule of ``package`` and return their names."""
    if isinstance(package, str):
        package = importlib.import_module(package)
    loaded: list[str] = []
    for directory in getattr(package, "__path__", []):
        for name in iter_module_names(directory):
            qualified = f"{package.__name__}.{name}"
            try:
                importlib.import_module(qualified)
            except ImportError as exc:
                log.warning("skipping plugin %s: %s", qualified, exc)
                continue
            loaded.append(qualified)
    log.debug("loaded %d plugin modules from %s", len(loaded), package.__name__)
    return loaded
