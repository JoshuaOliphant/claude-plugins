"""Exception hierarchy shared across the application."""


class StocklineError(Exception):
    """Base class for errors that the CLI reports without a traceback."""


class ConfigError(StocklineError):
    pass


class UnknownSupplierError(StocklineError):
    def __init__(self, hint: str):
        super().__init__(f"cannot determine supplier for {hint!r}")
        self.hint = hint


class FeedFormatError(StocklineError):
    def __init__(self, source: str, detail: str):
        super().__init__(f"{source}: {detail}")
        self.source = source
        self.detail = detail


class RejectThresholdExceeded(StocklineError):
    def __init__(self, rejected: int, seen: int, limit: float):
        super().__init__(
            f"{rejected} of {seen} rows rejected (limit {limit:.0%}); import aborted"
        )
        self.rejected = rejected
        self.seen = seen
        self.limit = limit


class StoreFormatError(StocklineError):
    pass
