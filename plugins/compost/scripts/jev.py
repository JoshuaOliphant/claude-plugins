#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typesafe-sdk>=0.7.1"]
# ///
# ABOUTME: Command line for compost's Jev tools: `jev.py <tool>` reads JSON input and prints a JSON judgment.
# ABOUTME: Exit 0 answered, 2 bad input, 3 Jev unavailable (no key or API failure: fall back to your own judgment).
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from jevtools import meta, review, spec, testing  # noqa: F401  (importing registers the tools)
from jevtools.core import Cache, Jev, Unavailable, open_client
from jevtools.registry import TOOLS, BadInput

EXIT_BAD_INPUT = 2
EXIT_UNAVAILABLE = 3


def read_input(source: str | None) -> dict:
    text = Path(source).read_text() if source and source != "-" else sys.stdin.read()
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError as error:
        raise BadInput(f"input is not JSON: {error}") from error
    if not isinstance(payload, dict):
        raise BadInput("input must be a JSON object")
    return payload


async def run(name: str, payload: dict, client_factory=open_client, cache: Cache | None = None) -> dict:
    selected = TOOLS[name]
    gathered = selected.gather(payload)
    cache = cache or Cache()
    async with client_factory() as client:
        jev = Jev(client, cache)
        result = await selected.judge(jev, gathered)
    cache.save()
    return {"tool": name, **result, "jev": {"input_tokens": jev.input_tokens, "cached": jev.cached}}


def main(argv: list[str] | None = None, client_factory=open_client) -> int:
    parser = argparse.ArgumentParser(prog="jev.py", description="compost's Jev tools")
    parser.add_argument("tool", choices=sorted([*TOOLS, "list"]))
    parser.add_argument("--input", help="JSON file with the tool's input; default stdin")
    args = parser.parse_args(argv)
    if args.tool == "list":
        for name, entry in sorted(TOOLS.items()):
            print(f"{name:16} {entry.summary}")
        return 0
    try:
        result = asyncio.run(run(args.tool, read_input(args.input), client_factory))
    except BadInput as error:
        print(f"bad input: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    except Unavailable as error:
        print(f"jev unavailable: {error}. Make this call yourself.", file=sys.stderr)
        return EXIT_UNAVAILABLE
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
