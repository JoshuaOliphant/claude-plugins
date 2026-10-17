#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typesafe-sdk>=0.7.1"]
# ///
# ABOUTME: Stop hook for compost:implement runs: blocks a stop that waits on the user for anything but an allowed stop.
# ABOUTME: A run ends when compost:finish loads; a message the user typed during the run makes waiting on them fine.
# ABOUTME: Jev's stop-guard tool judges the final message; any error or a missing key allows the stop and logs a line.
import asyncio
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jev
from jevtools import meta
from jevtools.core import open_client

LOG = Path.home() / ".cache" / "compost" / "stop-guard.log"
IMPLEMENT = "compost:implement"
FINISH = "compost:finish"
# Text Claude Code writes into user entries: <command-name>, <system-reminder>, <task-notification> and the like.
INJECTED = re.compile(r"<([a-z][a-z-]*)>.*?</\1>", re.DOTALL)
REASON = (
    "compost stop-guard: this implement run is unattended, and your last message waits on the user for something "
    f"outside the allowed stops ({'; '.join(meta.ALLOWED_STOPS)}). Decide it yourself, post a ruling as an issue "
    "comment (what, why, cost if wrong), and continue."
)


def entries(transcript: str) -> list[dict]:
    parsed = []
    for line in transcript.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            parsed.append(entry)
    return parsed


def blocks(entry: dict) -> list:
    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [block for block in content or [] if isinstance(block, dict)]


def loads(entry: dict, skill: str) -> bool:
    for block in blocks(entry):
        named = (block.get("input") or {}).get("skill")
        if block.get("type") == "tool_use" and block.get("name") == "Skill" and named == skill:
            return True
        command = f"<command-name>/{skill}</command-name>"
        if entry.get("type") == "user" and block.get("type") == "text" and command in block.get("text", ""):
            return True
    return False


def prompt(entry: dict) -> list[str]:
    """The text of a main-thread user entry that can start a turn; tool results and meta entries carry none."""
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return []
    return [block.get("text", "") for block in blocks(entry) if block.get("type") == "text"]


def typed(texts: list[str]) -> bool:
    """Whether the user typed a prompt, as opposed to Claude Code injecting it (<task-notification> and the like)."""
    return any(INJECTED.sub("", text).strip() for text in texts)


def unattended_run(transcript: list[dict]) -> bool:
    """An implement run is on (no compost:finish since it loaded) and the latest prompt since then is not typed."""
    starts = [index for index, entry in enumerate(transcript) if loads(entry, IMPLEMENT)]
    if not starts:
        return False
    since = transcript[starts[-1] + 1 :]
    if any(loads(entry, FINISH) for entry in since):
        return False
    prompts = [texts for texts in map(prompt, since) if texts]
    return not (prompts and typed(prompts[-1]))


def final_message(transcript: list[dict]) -> str:
    last_id, texts = None, []
    for entry in transcript:
        if entry.get("type") != "assistant" or entry.get("isSidechain"):
            continue
        said = [block["text"] for block in blocks(entry) if block.get("type") == "text" and block.get("text")]
        if not said:
            continue
        message_id = entry["message"].get("id")
        if message_id != last_id:
            last_id, texts = message_id, []
        texts.extend(said)
    return "\n".join(texts)


def decide(hook: dict, client_factory=open_client) -> dict | None:
    if hook.get("stop_hook_active"):
        return None
    text = Path(hook["transcript_path"]).read_text(errors="replace")
    if IMPLEMENT not in text:
        return None
    transcript = entries(text)
    if not unattended_run(transcript):
        return None
    message = hook.get("last_assistant_message") or final_message(transcript)
    if not message.strip():
        return None
    judgment = asyncio.run(jev.run("stop-guard", {"message": message}, client_factory))
    return {"decision": "block", "reason": REASON} if judgment["block"] else None


def log(line: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as handle:
        handle.write(f"{datetime.now(UTC).isoformat(timespec='seconds')} {line}\n")


def main(stdin=None, client_factory=open_client) -> int:
    try:
        verdict = decide(json.load(stdin or sys.stdin), client_factory)
    except Exception as error:  # noqa: BLE001 - a Stop hook must never trap the session; any failure allows the stop.
        log(f"allowed the stop after {type(error).__name__}: {error}")
        return 0
    if verdict:
        print(json.dumps(verdict))
    return 0


if __name__ == "__main__":
    sys.exit(main())
