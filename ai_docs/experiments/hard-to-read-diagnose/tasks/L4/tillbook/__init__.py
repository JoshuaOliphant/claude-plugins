"""Tillbook: point-of-sale ledger and reporting for multi-office retail.

Transactions are captured by the store tills of each office and exported as
JSON-lines files; refunds arrive separately from the payments provider as CSV.
Tillbook loads both, reconciles them against the office registry and produces
daily, weekly and item-level reports in the office's own calendar.
"""

__version__ = "2.4.1"
