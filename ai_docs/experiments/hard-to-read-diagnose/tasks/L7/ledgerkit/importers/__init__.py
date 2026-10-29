"""Input formats.

Like exporters, importers are discovered by importing every public module in
this package; each registers itself with :data:`importer_registry`.
"""

from __future__ import annotations

from ledgerkit.importers.base import ImportError_, ImportReport, Importer, importer_registry
from ledgerkit.utils.discovery import import_submodules

_loaded = False


def load_importers() -> None:
    global _loaded
    if _loaded:
        return
    import_submodules(__name__)
    _loaded = True


__all__ = ["ImportError_", "ImportReport", "Importer", "importer_registry", "load_importers"]
