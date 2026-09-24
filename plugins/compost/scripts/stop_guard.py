#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typesafe-sdk>=0.7.1"]
# ///
# ABOUTME: Stop hook for compost:implement runs: blocks a stop that waits on the user for anything but an allowed stop.
# ABOUTME: Jev's stop-guard tool judges the final message; any error or a missing key allows the stop and logs a line.
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jev
from jevtools import meta
from jevtools.core import open_client

LOG = Path.home() / ".cache" / "compost" / "stop-guard.log"
IMPLEMENT = "compost:implement"
COMMAND = f"<command-name>/{IMPLEMENT}</command-name>"
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


def loads_implement(entry: dict) -> bool:
    for block in blocks(entry):
        skill = (block.get("input") or {}).get("skill")
        if block.get("type") == "tool_use" and block.get("name") == "Skill" and skill == IMPLEMENT:
            return True
        if entry.get("type") == "user" and block.get("type") == "text" and COMMAND in block.get("text", ""):
            return True
    return False


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
    if not any(map(loads_implement, transcript)):
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
