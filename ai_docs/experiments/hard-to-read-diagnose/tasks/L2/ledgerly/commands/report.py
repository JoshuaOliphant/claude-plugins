"""``ledgerly report``: the summary report and the receivables aging table."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..reporting.formatting import format_money
from ..reporting.sections import aging_section
from ..reporting.summary import build_summary
from ..services import payments as payment_service
from ..utils import dates
from ._common import (
    CommandError,
    add_common_args,
    add_source_arg,
    as_of_arg,
    build_service,
    load_payments,
    load_source,
    run,
)

SECTIONS = ("totals", "customers", "trend", "forecast", "aging")


def _sections(text: str | None) -> tuple[str, ...]:
    if not text:
        return SECTIONS
    chosen = tuple(part.strip() for part in text.split(",") if part.strip())
    unknown = [name for name in chosen if name not in SECTIONS]
    if unknown:
        raise CommandError(f"unknown section(s): {', '.join(unknown)}")
    return chosen


def cmd_summary(args) -> int:
    service = build_service(args)
    invoices = load_source(service, args.source)
    payments = load_payments(args.payments)
    as_of = args.as_of or dates.today()
    report = build_summary(service, invoices, args.source, as_of, payments, _sections(args.only))
    print(report.render(), end="")
    return 0


def cmd_aging(args) -> int:
    service = build_service(args)
    invoices = load_source(service, args.source)
    payments = load_payments(args.payments) or []
    as_of = args.as_of or dates.today()
    settings = service.settings
    balances = payment_service.apply_payments(invoices, payments, service.rates)
    buckets = payment_service.aging(
        balances, as_of, settings.due_days, settings.aging_buckets, settings.base_currency
    )
    print("\n".join(aging_section(buckets).render()).rstrip())
    total = payment_service.outstanding(balances, settings.base_currency)
    print(f"Total outstanding: {format_money(total)}")
    return 0


def main(argv) -> int:
    parser = argparse.ArgumentParser(prog="ledgerly report")
    sub = parser.add_subparsers(dest="action", required=True)

    summary = sub.add_parser("summary", help="ledger summary report")
    add_source_arg(summary)
    add_common_args(summary)
    summary.add_argument("--payments", type=Path)
    summary.add_argument("--as-of", type=as_of_arg)
    summary.add_argument("--only", help=f"comma-separated subset of: {','.join(SECTIONS)}")
    summary.set_defaults(handler=cmd_summary)

    aging = sub.add_parser("aging", help="receivables aging")
    add_source_arg(aging)
    add_common_args(aging)
    aging.add_argument("--payments", type=Path, required=True)
    aging.add_argument("--as-of", type=as_of_arg)
    aging.set_defaults(handler=cmd_aging)

    args = parser.parse_args(argv)
    return run(args.handler, args)
