"""Output formats.

Every public module in this package is imported by :func:`load_exporters`;
exporter classes register themselves on import.
"""

from __future__ import annotations

from ledgerkit.exporters.base import ExportOptions, Exporter, exporter_registry
from ledgerkit.utils.discovery import import_submodules

_loaded = False


def load_exporters() -> None:
    global _loaded
    if _loaded:
        return
    import_submodules(__name__)
    _loaded = True


__all__ = ["ExportOptions", "Exporter", "exporter_registry", "load_exporters"]
