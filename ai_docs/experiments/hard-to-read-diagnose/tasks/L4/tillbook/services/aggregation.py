"""Fold transactions into report rows."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable

from tillbook.adapters.fx import FxTable
from tillbook.domain.models import DailyTotal, ItemTotal, Kind, Transaction
from tillbook.domain.money import Money
from tillbook.domain.offices import Office


def daily_total(office: Office, day: date, transactions: Iterable[Transaction]) -> DailyTotal:
    row = DailyTotal(office=office.code, day=day, currency=office.currency)
    for txn in transactions:
        if txn.amount.currency != office.currency:
            raise ValueError(
                f"{txn.txn_id}: {txn.amount.currency} transaction in {office.currency} office"
            )
        tender = txn.tender.value
        if txn.kind is Kind.SALE:
            row.sales_count += 1
            row.gross = row.gross + txn.amount
            row.by_tender[tender] = row.by_tender.get(tender, Money.zero(office.currency)) + txn.amount
            if row.first_sale is None or txn.at < row.first_sale:
                row.first_sale = txn.at
            if row.last_sale is None or txn.at > row.last_sale:
                row.last_sale = txn.at
        elif txn.kind is Kind.REFUND:
            row.refund_count += 1
            row.refunds = row.refunds + txn.amount
            row.by_tender[tender] = row.by_tender.get(tender, Money.zero(office.currency)) - txn.amount
        else:
            row.void_count += 1
    return row


def item_totals(transactions: Iterable[Transaction], currency: str) -> list[ItemTotal]:
    quantities: dict[str, int] = defaultdict(int)
    revenue: dict[str, Money] = {}
    names: dict[str, str] = {}
    for txn in transactions:
        if txn.kind is not Kind.SALE:
            continue
        for item in txn.items:
            quantities[item.sku] += item.quantity
            revenue[item.sku] = revenue.get(item.sku, Money.zero(currency)) + item.amount
            names.setdefault(item.sku, item.description)
    rows = [
        ItemTotal(sku=sku, description=names[sku], quantity=quantities[sku], revenue=revenue[sku])
        for sku in quantities
    ]
    rows.sort(key=lambda row: (-row.revenue.minor, row.sku))
    return rows


def converted_net(transactions: Iterable[Transaction], fx: FxTable, target: str) -> Money:
    result = Money.zero(target)
    for txn in transactions:
        signed = txn.signed_amount
        if not signed:
            continue
        result = result + fx.convert(signed, txn.epoch, target)
    return result


def hourly_profile(office: Office, transactions: Iterable[Transaction]) -> list[int]:
    """Sale counts per office-local hour of day."""
    counts = [0] * 24
    for txn in transactions:
        if txn.kind is Kind.SALE:
            counts[office.local(txn.at).hour] += 1
    return counts
