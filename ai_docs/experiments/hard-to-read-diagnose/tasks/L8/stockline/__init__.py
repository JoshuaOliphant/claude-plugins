"""Stockline: supplier feed ingestion for the product catalog.

Suppliers drop price/availability feeds (CSV or JSON lines) every night.
``stockline import`` maps each feed onto the catalog, recomputes sell
prices from the pricing rules and records every change in the journal.
"""

__version__ = "2.7.1"
