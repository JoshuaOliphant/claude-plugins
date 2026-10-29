"""Command line interface.

    python -m basketry summarize samples/requests.jsonl
    python -m basketry summarize --format json - < requests.jsonl
    python -m basketry catalog
    python -m basketry customers --tier gold
    python -m basketry serve --port 8080
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator, Sequence
from typing import IO, Any

from . import api
from .adapters import render as _renderers  # noqa: F401  (registers renderers)
from .utils.registry import get_renderer, renderer_names
from .utils.text import money, rule, two_column


def _read_requests(stream: IO[str]) -> Iterator[tuple[int, Any]]:
    for number, line in enumerate(stream, start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            yield number, json.loads(line)
        except json.JSONDecodeError as exc:
            yield number, exc


def cmd_summarize(args: argparse.Namespace, out: IO[str], err: IO[str]) -> int:
    renderer = get_renderer(args.format)
    service = api.get_service()
    stream = sys.stdin if args.requests == "-" else open(args.requests, encoding="utf-8")
    failures = 0
    first = True
    try:
        for number, payload in _read_requests(stream):
            if isinstance(payload, Exception):
                print(f"line {number}: invalid JSON: {payload}", file=err)
                failures += 1
                continue
            try:
                summary = service.summarize(payload)
            except (ValueError, LookupError) as exc:
                print(f"line {number}: rejected: {exc}", file=err)
                failures += 1
                continue
            if args.customer and summary.customer_id != args.customer:
                continue
            if args.format == "text" and not first:
                print("", file=out)
                print(rule("="), file=out)
                print("", file=out)
            print(renderer(summary), file=out)
            first = False
    finally:
        if stream is not sys.stdin:
            stream.close()
    if args.journal:
        print("", file=err)
        for entry in service.journal:
            print(entry.describe(), file=err)
    return 1 if failures and args.strict else 0


def cmd_catalog(args: argparse.Namespace, out: IO[str], err: IO[str]) -> int:
    catalog = api.get_service().catalog
    for product in catalog:
        if args.category and product.category != args.category:
            continue
        flag = " (giftable)" if product.giftable else ""
        print(two_column(f"{product.sku:<12} {product.name}{flag}", money(product.price_cents)), file=out)
    return 0


def cmd_customers(args: argparse.Namespace, out: IO[str], err: IO[str]) -> int:
    store = api.get_service().decoder.customers
    customers = store.by_tier(args.tier) if args.tier else store.all()
    for customer in customers:
        tags = f" [{', '.join(customer.tags)}]" if customer.tags else ""
        print(f"{customer.customer_id}  {customer.name:<20} {customer.tier:<8} {customer.region}{tags}", file=out)
    return 0


def cmd_serve(args: argparse.Namespace, out: IO[str], err: IO[str]) -> int:
    from .adapters.http import serve

    serve(args.host, args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="basketry", description="Order summaries for the basketry shop.")
    sub = parser.add_subparsers(dest="command", required=True)

    summarize = sub.add_parser("summarize", help="summarize order requests from a JSON-lines file")
    summarize.add_argument("requests", help="path to a .jsonl file of order requests, or - for stdin")
    summarize.add_argument("--format", choices=renderer_names(), default="text")
    summarize.add_argument("--customer", help="only print summaries for this customer id")
    summarize.add_argument("--journal", action="store_true", help="print the audit journal to stderr")
    summarize.add_argument("--strict", action="store_true", help="exit non-zero if any request is rejected")
    summarize.set_defaults(func=cmd_summarize)

    catalog = sub.add_parser("catalog", help="list products")
    catalog.add_argument("--category")
    catalog.set_defaults(func=cmd_catalog)

    customers = sub.add_parser("customers", help="list customers")
    customers.add_argument("--tier", choices=["standard", "silver", "gold"])
    customers.set_defaults(func=cmd_customers)

    serve = sub.add_parser("serve", help="run the HTTP API (development server)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.set_defaults(func=cmd_serve)
    return parser


def main(argv: Sequence[str] | None = None, out: IO[str] | None = None, err: IO[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args, out or sys.stdout, err or sys.stderr)
