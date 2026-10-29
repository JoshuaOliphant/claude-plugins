"""Command-line entry point.

Usage: ``python -m ledgerly <command> <action> [options]``

Command modules are imported on demand so that ``ledgerly --help`` and the
quick commands do not pay for loading the reporting stack.
"""

from __future__ import annotations

import importlib
import sys

from . import __version__

COMMANDS = {
    "invoice": ("ledgerly.commands.invoice", "invoice totals, listings and detail"),
    "report": ("ledgerly.commands.report", "summary and aging reports"),
    "export": ("ledgerly.commands.export", "export invoice totals as JSON/CSV"),
}


def usage() -> str:
    lines = [f"ledgerly {__version__}", "", "usage: ledgerly <command> [args...]", "", "commands:"]
    for name, (_, help_text) in COMMANDS.items():
        lines.append(f"  {name:<10}{help_text}")
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(usage())
        return 0 if argv else 1
    if argv[0] == "--version":
        print(__version__)
        return 0
    name, rest = argv[0], argv[1:]
    try:
        module_name, _ = COMMANDS[name]
    except KeyError:
        print(f"unknown command: {name}\n\n{usage()}", file=sys.stderr)
        return 2
    module = importlib.import_module(module_name)
    return module.main(rest)


if __name__ == "__main__":
    sys.exit(main())
