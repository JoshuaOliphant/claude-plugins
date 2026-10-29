"""Decode raw export records into ``Transaction`` objects.

Two till firmware generations are in the field. Current tills write ``ts``
as integer epoch seconds; the older ones write ``captured_at`` as an
ISO-8601 string with the store's UTC offset. Both decode to the same
instant.
"""

from __future__ import annotations

from typing import Any, Mapping

from tillbook.domain.models import Kind, LineItem, Tender, Transaction
from tillbook.domain.money import Money
from tillbook.utils.timeconv import TimestampError, from_epoch, parse_iso


class DecodeError(ValueError):
    def __init__(self, message: str, record: Mapping[str, Any] | None = None, where: str = ""):
        super().__init__(message)
        self.record = record
        self.where = where

    def __str__(self) -> str:
        prefix = f"{self.where}: " if self.where else ""
        return prefix + super().__str__()


def _instant(record: Mapping[str, Any]):
    if "ts" in record and record["ts"] is not None:
        value = record["ts"]
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise DecodeError(f"bad ts {value!r}", record)
        seconds = int(float(value))
        return seconds, from_epoch(seconds)
    if "captured_at" in record:
        try:
            moment = parse_iso(str(record["captured_at"]))
        except TimestampError as exc:
            raise DecodeError(str(exc), record) from exc
        return int(moment.timestamp()), moment
    raise DecodeError("record has neither ts nor captured_at", record)


def _items(raw_items: Any, currency: str) -> tuple[LineItem, ...]:
    if not raw_items:
        return ()
    items = []
    for raw in raw_items:
        quantity = int(raw.get("qty", 1))
        if quantity <= 0:
            raise DecodeError(f"non-positive quantity for {raw.get('sku')!r}")
        items.append(
            LineItem(
                sku=str(raw["sku"]),
                description=str(raw.get("desc", "")),
                quantity=quantity,
                unit_price=Money.parse(str(raw["price"]), currency),
            )
        )
    return tuple(items)


def decode_till_record(record: Mapping[str, Any], source: str = "") -> Transaction:
    try:
        currency = str(record["currency"]).upper()
        kind = Kind(str(record.get("kind", "sale")).lower())
        tender = Tender.parse(str(record.get("tender", "card")))
        epoch, moment = _instant(record)
        items = _items(record.get("items"), currency)
        if items:
            amount = Money.zero(currency)
            for item in items:
                amount = amount + item.amount
            declared = record.get("amount")
            if declared is not None and Money.parse(str(declared), currency) != amount:
                raise DecodeError(
                    f"declared amount {declared} does not match line items {amount.to_json()}",
                    record,
                )
        else:
            amount = Money.parse(str(record.get("amount", "0")), currency)
        return Transaction(
            txn_id=str(record["id"]),
            office=str(record["office"]).upper(),
            till=str(record.get("till", "")),
            kind=kind,
            tender=tender,
            epoch=epoch,
            at=moment,
            amount=amount,
            items=items,
            reference=record.get("ref"),
            source=source,
        )
    except DecodeError as exc:
        exc.where = exc.where or source
        raise
    except (KeyError, ValueError, TypeError) as exc:
        raise DecodeError(f"{type(exc).__name__}: {exc}", record, source) from exc


def decode_refund_row(row: Mapping[str, str], source: str = "") -> Transaction:
    try:
        currency = row["currency"].strip().upper()
        moment = parse_iso(row["processed_at"])
        return Transaction(
            txn_id=row["refund_id"].strip(),
            office=row["office"].strip().upper(),
            till=row.get("till", "").strip() or "PSP",
            kind=Kind.REFUND,
            tender=Tender.parse(row.get("tender", "card")),
            epoch=int(moment.timestamp()),
            at=moment,
            amount=Money.parse(row["amount"], currency),
            reference=row.get("original_txn", "").strip() or None,
            source=source,
        )
    except (KeyError, ValueError, TimestampError) as exc:
        raise DecodeError(f"{type(exc).__name__}: {exc}", dict(row), source) from exc
