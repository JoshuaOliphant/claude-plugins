"""Database access: connections, transactions and migrations."""

from stockroom.db.connection import connect, open_default
from stockroom.db.transaction import transaction

__all__ = ["connect", "open_default", "transaction"]
