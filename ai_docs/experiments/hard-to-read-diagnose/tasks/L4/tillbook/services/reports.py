"""Report builders used by the command line."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from tillbook.adapters.fx import FxTable
from tillbook.domain.models import DailyTotal, Kind
from tillbook.services import aggregation
from tillbook.services.ledger import LedgerService
from tillbook.utils.formatting import plural, render_table, to_json
from tillbook.utils.timeconv import week_start


@dataclass
class Rendered:
    payload: dict
    text: str

    def as_json(self) -> str:
        return to_json(self.payload)


def _header(title: str) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"{title}\n(generated {generated} server time)\n"


def _daily_rows(rows: list[DailyTotal]) -> list[list]:
    return [
        [row.day.isoformat(), row.sales_count, row.refund_count, row.void_count,
         row.gross.format(), row.refunds.format(), row.net.format()]
        for row in rows
    ]


DAILY_HEADERS = ["date", "sales", "refunds", "voids", "gross", "refunded", "net"]
DAILY_ALIGN = ["<", ">", ">", ">", ">", ">", ">"]


class ReportService:
    def __init__(self, ledger: LedgerService, fx: FxTable, report_currency: str = "USD",
                 week_starts_on: int = 0) -> None:
        self.ledger = ledger
        self.fx = fx
        self.report_currency = report_currency
        self.week_starts_on = week_starts_on

    def daily_total(self, office_code: str, day: date) -> DailyTotal:
        office = self.ledger.office(office_code)
        return aggregation.daily_total(office, day, self.ledger.transactions_on(office.code, day))

    def daily_totals(self, office_code: str, first: date, last: date | None = None) -> Rendered:
        office = self.ledger.office(office_code)
        last = last or first
        by_day = self.ledger.transactions_between(office.code, first, last)
        rows = [aggregation.daily_total(office, day, txns) for day, txns in by_day.items()]
        payload = {
            "office": office.code,
            "timezone": office.timezone,
            "currency": office.currency,
            "days": [row.to_json() for row in rows],
        }
        lines = [_header(f"Daily totals - {office.name} ({office.code}), {office.currency}")]
        lines.append(render_table(DAILY_HEADERS, _daily_rows(rows), DAILY_ALIGN))
        if len(rows) > 1:
            gross = sum((r.gross.minor for r in rows))
            net = sum((r.net.minor for r in rows))
            lines.append(f"\n{plural(len(rows), 'day')}: gross {gross / 100:,.2f}, net {net / 100:,.2f}")
        return Rendered(payload, "\n".join(lines))

    def weekly(self, office_code: str, any_day: date) -> Rendered:
        office = self.ledger.office(office_code)
        start = week_start(any_day, self.week_starts_on)
        end = start + timedelta(days=6)
        by_day = self.ledger.transactions_between(office.code, start, end)
        rows = [aggregation.daily_total(office, day, txns) for day, txns in by_day.items()]
        all_txns = [txn for txns in by_day.values() for txn in txns]
        profile = aggregation.hourly_profile(office, all_txns)
        busiest = max(range(24), key=lambda hour: (profile[hour], -hour)) if any(profile) else None
        payload = {
            "office": office.code,
            "week_start": start.isoformat(),
            "week_end": end.isoformat(),
            "days": [row.to_json() for row in rows],
            "net": sum(r.net.minor for r in rows) / 100,
            "busiest_hour": busiest,
        }
        lines = [_header(f"Week of {start.isoformat()} - {office.name} ({office.code})")]
        lines.append(render_table(DAILY_HEADERS, _daily_rows(rows), DAILY_ALIGN))
        if busiest is not None:
            lines.append(f"\nbusiest hour: {busiest:02d}:00-{busiest:02d}:59 local "
                         f"({plural(profile[busiest], 'sale')})")
        return Rendered(payload, "\n".join(lines))

    def top_items(self, office_code: str, first: date, last: date, limit: int = 10) -> Rendered:
        office = self.ledger.office(office_code)
        by_day = self.ledger.transactions_between(office.code, first, last)
        txns = [txn for day_txns in by_day.values() for txn in day_txns]
        items = aggregation.item_totals(txns, office.currency)[:limit]
        payload = {
            "office": office.code,
            "from": first.isoformat(),
            "to": last.isoformat(),
            "items": [item.to_json() for item in items],
        }
        lines = [_header(f"Top items {first} to {last} - {office.name}")]
        lines.append(render_table(
            ["sku", "description", "qty", "revenue"],
            [[i.sku, i.description, i.quantity, i.revenue.format()] for i in items],
            ["<", "<", ">", ">"],
        ))
        return Rendered(payload, "\n".join(lines))

    def consolidated(self, day: date) -> Rendered:
        """Net takings for every office on its own ``day``, in the report currency."""
        rows = []
        grand = 0
        for office in self.ledger.offices:
            txns = self.ledger.transactions_on(office.code, day)
            net_local = aggregation.daily_total(office, day, txns).net
            net_report = aggregation.converted_net(txns, self.fx, self.report_currency)
            grand += net_report.minor
            rows.append({
                "office": office.code,
                "transactions": len(txns),
                "sales": sum(1 for t in txns if t.kind is Kind.SALE),
                "net_local": net_local.to_json(),
                "currency": office.currency,
                "net_report": net_report.to_json(),
            })
        payload = {"date": day.isoformat(), "report_currency": self.report_currency,
                   "offices": rows, "total": f"{grand / 100:.2f}"}
        lines = [_header(f"Consolidated net for {day.isoformat()} ({self.report_currency})")]
        lines.append(render_table(
            ["office", "txns", "sales", "net (local)", "ccy", f"net ({self.report_currency})"],
            [[r["office"], r["transactions"], r["sales"], r["net_local"], r["currency"],
              r["net_report"]] for r in rows],
            ["<", ">", ">", ">", "<", ">"],
        ))
        lines.append(f"\ntotal: {grand / 100:,.2f} {self.report_currency}")
        return Rendered(payload, "\n".join(lines))
