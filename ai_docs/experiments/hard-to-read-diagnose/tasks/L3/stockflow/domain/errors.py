"""Exception hierarchy shared across the application."""

from __future__ import annotations


class StockflowError(Exception):
    """Base class for all application errors."""


class ConfigError(StockflowError):
    """Raised when the configuration file is missing or malformed."""


class CatalogError(StockflowError):
    """Raised when the SKU catalog cannot be loaded."""


class UnknownServiceError(StockflowError):
    """Raised when a service is requested that was never registered."""

    def __init__(self, name: str) -> None:
        super().__init__(f"no service registered under {name!r}")
        self.name = name


class UnitError(StockflowError):
    """Raised for unknown or inconsistent units of measure."""


class ValidationError(StockflowError):
    """Raised when a single input row cannot be turned into a movement."""

    def __init__(self, source: str, line_no: int, reason: str) -> None:
        super().__init__(f"{source}:{line_no}: {reason}")
        self.source = source
        self.line_no = line_no
        self.reason = reason


class InputFormatError(StockflowError):
    """Raised when an input file is not a usable movement file at all."""
