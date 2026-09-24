# ABOUTME: The table of compost's Jev tools. Each tool pairs a gather step (reads the repo, no Jev)
# ABOUTME: with a judge step (asks Jev, applies thresholds in code); jev.py looks tools up here by name.
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


class BadInput(Exception):
    pass


@dataclass(frozen=True)
class Tool:
    name: str
    summary: str
    gather: Callable[[dict], dict]
    judge: Callable[..., Awaitable[dict]]


TOOLS: dict[str, Tool] = {}


def tool(name: str, summary: str, gather: Callable[[dict], dict]):
    def register(judge):
        TOOLS[name] = Tool(name, summary, gather, judge)
        return judge

    return register


def require(payload: dict, *keys: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise BadInput(f"input is missing {', '.join(missing)}")
