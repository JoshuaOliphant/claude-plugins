"""Command-line interface: ``python -m relaydesk <command>``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, bootstrap, reporting
from .adapters.state import DeliveryState
from .adapters.ticket_source import TicketSource
from .domain import priority
from .services.dispatcher import Dispatcher
from .services.templates import TemplateStore
from .settings import SettingError
from .utils import text
from .utils.timeutil import parse_iso, utcnow


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", help="project directory (default: discovered from cwd)")
    parser.add_argument("--config", help="config file (default: config/relaydesk.toml)")
    parser.add_argument("-v", "--verbose", action="count", default=0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="relaydesk",
                                     description="Relay help-desk tickets to chat webhooks.")
    parser.add_argument("--version", action="version", version=f"relaydesk {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    send = sub.add_parser("send", help="route, batch and deliver notifications")
    _common(send)
    send.add_argument("--dry-run", action="store_true", help="plan batches, deliver nothing")
    send.add_argument("--json", action="store_true", help="one JSON object per batch")
    send.add_argument("--batch-size", type=int, help="override delivery.batch_size")
    send.add_argument("--transport", choices=("outbox", "webhook"),
                      help="override delivery.transport")
    send.add_argument("--endpoint", help="override delivery.endpoint")
    send.add_argument("--include-closed", action="store_const", const=True,
                      help="also notify about closed tickets")
    send.add_argument("--as-of", help="reference time for ages/scores (ISO-8601)")

    lst = sub.add_parser("list", help="show the most pressing tickets")
    _common(lst)
    lst.add_argument("--limit", type=int, default=20)
    lst.add_argument("--status", help="only tickets with this status")
    lst.add_argument("--category", help="only tickets in this category")
    lst.add_argument("--as-of", help="reference time for ages/scores (ISO-8601)")

    cfg = sub.add_parser("config", help="print the effective configuration")
    _common(cfg)
    cfg.add_argument("--json", action="store_true")

    stats = sub.add_parser("stats", help="counts by status, category and priority")
    _common(stats)

    tpl = sub.add_parser("templates", help="list available message templates")
    _common(tpl)

    reset = sub.add_parser("reset-state", help="forget which tickets were delivered")
    _common(reset)
    return parser


def _overrides(args: argparse.Namespace) -> dict[str, object]:
    return {
        "delivery.batch_size": getattr(args, "batch_size", None),
        "delivery.transport": getattr(args, "transport", None),
        "delivery.endpoint": getattr(args, "endpoint", None),
        "routing.include_closed": getattr(args, "include_closed", None),
    }


def _as_of(args: argparse.Namespace):
    raw = getattr(args, "as_of", None)
    return parse_iso(raw) if raw else utcnow()


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    return value


def cmd_send(args, settings) -> int:
    dispatcher = Dispatcher(settings, _as_of(args), dry_run=args.dry_run)
    report = dispatcher.run()
    if args.json:
        for line in reporting.batches_json(report):
            print(line)
    else:
        print(reporting.summary(report, args.dry_run))
    return 1 if report.failed else 0


def cmd_list(args, settings) -> int:
    now = _as_of(args)
    tickets = TicketSource(settings.path("sources.tickets")).load()
    if args.status:
        tickets = [t for t in tickets if t.status.value == args.status]
    if args.category:
        tickets = [t for t in tickets if t.category == args.category]
    ranked = priority.order(tickets, now)[: max(args.limit, 0)]
    rows = [[t.id, str(priority.score(t, now)), t.priority.value, t.status.value,
             t.category, text.truncate(t.subject, 48)] for t in ranked]
    print(text.table(rows, ["id", "score", "priority", "status", "category", "subject"]))
    return 0


def cmd_config(args, settings) -> int:
    if args.json:
        data = {k: _jsonable(v) for k, v in sorted(settings.as_dict().items())}
        print(json.dumps(data, indent=2))
    else:
        print(f"# {settings.config_path}")
        print(reporting.settings_table(settings))
    return 0


def cmd_stats(args, settings) -> int:
    tickets = TicketSource(settings.path("sources.tickets")).load()
    print(reporting.ticket_stats(tickets))
    return 0


def cmd_templates(args, settings) -> int:
    store = TemplateStore(settings.path("templates.dir"))
    for name in store.available():
        print(f"{name:12} {store.get(name).source}")
    return 0


def cmd_reset_state(args, settings) -> int:
    state = DeliveryState(settings.path("state.db"))
    removed = state.forget()
    state.close()
    print(f"forgot {removed} delivered ticket(s)")
    return 0


COMMANDS = {
    "send": cmd_send,
    "list": cmd_list,
    "config": cmd_config,
    "stats": cmd_stats,
    "templates": cmd_templates,
    "reset-state": cmd_reset_state,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = bootstrap.start(args.root, args.config, _overrides(args), args.verbose)
    except SettingError as exc:
        print(f"relaydesk: configuration error: {exc}", file=sys.stderr)
        return 2
    return COMMANDS[args.command](args, settings)
