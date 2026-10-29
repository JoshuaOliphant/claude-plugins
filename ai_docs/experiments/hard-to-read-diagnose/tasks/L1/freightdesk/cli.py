"""Command-line interface.

Examples::

    python -m freightdesk quote --to DE-80331 --parcel 40x30x20@2.5
    python -m freightdesk quote --carrier ALPENPOST --to AT-1010 --dims 30x20x10 --weight 1.2
    python -m freightdesk batch data/samples/manifest-2026-10.csv --format csv
    python -m freightdesk shop --to NL-1012AB --parcel 50x40x30@4
    python -m freightdesk tariff NORDLINE
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from freightdesk import __version__
from freightdesk.adapters.render import formats, render, render_many
from freightdesk.config import load_settings
from freightdesk.domain.errors import FreightError, ValidationError
from freightdesk.domain.shipment import Parcel
from freightdesk.pricing.tariffs import available_carriers, get_tariff
from freightdesk.pricing.zones import served_lanes
from freightdesk.services.quoting import QuoteRequest, QuoteService
from freightdesk.services.reporting import format_summary, summarise, zone_histogram
from freightdesk.utils import diskcache
from freightdesk.utils.log import configure


def _destination(value: str) -> tuple[str, str]:
    if "-" not in value:
        raise argparse.ArgumentTypeError("destination must look like DE-80331")
    country, postcode = value.split("-", 1)
    return country.strip().upper(), postcode.strip()


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an ISO date: {value!r}") from None


def _parcels(args: argparse.Namespace) -> list[Parcel]:
    parcels = [Parcel.parse(spec) for spec in args.parcel or []]
    if args.dims or args.weight:
        if not (args.dims and args.weight):
            raise ValidationError("--dims and --weight must be given together")
        parcels.append(Parcel.from_strings(args.dims, args.weight))
    if not parcels:
        raise ValidationError("give at least one --parcel (or --dims with --weight)")
    return parcels


def _add_shipment_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--to", required=True, type=_destination, metavar="CC-POSTCODE")
    p.add_argument("--from", dest="origin", type=_destination, metavar="CC-POSTCODE")
    p.add_argument("--parcel", action="append", metavar="LxWxH@KG")
    p.add_argument("--dims", metavar="LxWxH")
    p.add_argument("--weight", metavar="KG")
    p.add_argument("--residential", action="store_true")
    p.add_argument("--express", action="store_true")
    p.add_argument("--saturday", action="store_true")
    p.add_argument("--currency")
    p.add_argument("--ship-date", type=_date, default=None)
    p.add_argument("--reference", default="")
    p.add_argument("--format", choices=formats(), default="text")


def _request(args: argparse.Namespace, carrier: str) -> QuoteRequest:
    country, postcode = args.to
    origin_country, origin_postcode = args.origin if args.origin else (None, None)
    return QuoteRequest(
        carrier=carrier,
        dest_country=country,
        dest_postcode=postcode,
        parcels=_parcels(args),
        ship_date=args.ship_date or date.today(),
        origin_country=origin_country,
        origin_postcode=origin_postcode,
        residential=args.residential,
        service="express" if args.express else "standard",
        currency=args.currency,
        reference=args.reference,
        options={"saturday"} if args.saturday else set(),
    )


def cmd_quote(args: argparse.Namespace) -> int:
    service = QuoteService()
    carrier = (args.carrier or service.settings.default_carrier).upper()
    quote = service.quote(_request(args, carrier))
    print(render(quote, args.format))
    return 0


def cmd_shop(args: argparse.Namespace) -> int:
    service = QuoteService()
    quotes = service.rate_shop(_request(args, service.settings.default_carrier))
    if not quotes:
        print("no carrier serves this lane", file=sys.stderr)
        return 3
    print(render_many(quotes, args.format))
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    service = QuoteService()
    result = service.quote_manifest(Path(args.manifest), args.ship_date or date.today(), args.currency)
    if args.summary:
        print(format_summary(summarise(result.quotes), result.failures))
        if args.format == "text":
            for carrier, zones in zone_histogram(result.quotes).items():
                print(f"{carrier}: " + ", ".join(f"zone {z}: {n}" for z, n in zones.items()))
    else:
        print(render_many(result.quotes, args.format))
        for ref, reason in result.failures:
            print(f"warning: {ref}: {reason}", file=sys.stderr)
    return 1 if result.failures and args.strict else 0


def cmd_tariff(args: argparse.Namespace) -> int:
    if not args.carrier:
        for code in available_carriers():
            t = get_tariff(code)
            print(f"{t.code:<10} {t.revision:<8} {t.name}")
        return 0
    t = get_tariff(args.carrier)
    print(f"{t.name} ({t.code}), revision {t.revision}, prices in {t.currency}")
    print(f"  fuel surcharge {t.fuel_surcharge_pct}%, express x{t.express_multiplier}")
    print(f"  weight step {t.weight_step_kg} kg, max {t.max_weight_kg} kg")
    for zone in sorted(t.bands):
        bands = ", ".join(f"<={b.upper_kg}: {b.price}" for b in t.bands[zone])
        print(f"  zone {zone}: {bands}")
    for name, amount in sorted(t.surcharges.items()):
        print(f"  surcharge {name}: {amount}")
    return 0


def cmd_lanes(args: argparse.Namespace) -> int:
    for origin, dest, zone in served_lanes(args.carrier):
        print(f"{origin} -> {dest}: {zone}")
    return 0


def cmd_cache(args: argparse.Namespace) -> int:
    root = load_settings().cache_dir
    report = {}
    if root.is_dir():
        for ns_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            cache = diskcache.DiskCache(root=root, namespace=ns_dir.name)
            report[ns_dir.name] = len(cache.entries())
    if args.json:
        print(json.dumps({"cache_dir": str(root), "entries": report}, indent=2))
    else:
        print(f"cache directory: {root}")
        for ns, count in report.items():
            print(f"  {ns:<16} {count:>6} entries")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="freightdesk", description="Parcel rating for the shipping desk")
    parser.add_argument("--version", action="version", version=f"freightdesk {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("quote", help="quote one shipment")
    p.add_argument("--carrier")
    _add_shipment_args(p)
    p.set_defaults(func=cmd_quote)

    p = sub.add_parser("shop", help="compare all carriers for one shipment")
    _add_shipment_args(p)
    p.set_defaults(func=cmd_shop)

    p = sub.add_parser("batch", help="quote every shipment in a manifest CSV")
    p.add_argument("manifest")
    p.add_argument("--ship-date", type=_date, default=None)
    p.add_argument("--currency")
    p.add_argument("--format", choices=formats(), default="text")
    p.add_argument("--summary", action="store_true")
    p.add_argument("--strict", action="store_true", help="exit 1 if any shipment fails")
    p.set_defaults(func=cmd_batch)

    p = sub.add_parser("tariff", help="show carrier rate cards")
    p.add_argument("carrier", nargs="?")
    p.set_defaults(func=cmd_tariff)

    p = sub.add_parser("lanes", help="list the lanes a carrier serves")
    p.add_argument("carrier")
    p.set_defaults(func=cmd_lanes)

    p = sub.add_parser("cache", help="show persistent cache usage")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_cache)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure(load_settings().log_level)
    try:
        return args.func(args)
    except FreightError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
