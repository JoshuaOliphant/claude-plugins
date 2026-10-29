"""Exceptions raised by services. The CLI maps them to exit codes."""


class StockroomError(Exception):
    exit_code = 1


class ValidationError(StockroomError):
    exit_code = 2


class NotFound(StockroomError):
    exit_code = 3


class InsufficientStock(StockroomError):
    exit_code = 4

    def __init__(self, sku: str, warehouse: str, requested: int, available: int):
        self.sku = sku
        self.warehouse = warehouse
        self.requested = requested
        self.available = available
        super().__init__(
            f"insufficient stock for {sku} at {warehouse}: "
            f"requested {requested}, available {available}"
        )


class InvalidState(StockroomError):
    exit_code = 5
