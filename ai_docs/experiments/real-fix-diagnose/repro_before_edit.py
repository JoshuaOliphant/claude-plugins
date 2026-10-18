# ABOUTME: Reads subagent transcripts (JSONL) and reports, per run, whether anything exercised the code before the first edit to scripts/ (#171).
# ABOUTME: Usage: repro_before_edit.py <dir of *.output transcripts>; run label comes from the briefs/<arm>/tN.md path in each transcript.
import json
import re
import sys
from pathlib import Path

MUTATES = re.compile(r"sed -i|write_text\(|open\([^)]*['\"]w['\"]|\.write\(|tee ")
EXERCISES = re.compile(r"python|pytest")


def blocks(event: dict) -> list:
    content = event.get("message", {}).get("content")
    return content if isinstance(content, list) else []


def mutating(call: dict) -> bool:
    data = call["input"]
    if call["name"] in ("Edit", "Write"):
        return "/scripts/" in data.get("file_path", "")
    command = data.get("command", "")
    return (
        call["name"] == "Bash"
        and bool(MUTATES.search(command))
        and ("scripts" in command or "sed -i" in command)
    )


def main() -> None:
    for path in sorted(Path(sys.argv[1]).glob("*.output")):
        events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        label = re.search(r"briefs/([a-z-]+)/(t\d+)\.md", json.dumps(events[:3]))
        if not label:
            continue
        calls = [b for e in events for b in blocks(e) if b.get("type") == "tool_use"]
        first = next((i for i, c in enumerate(calls) if mutating(c)), len(calls))
        ran = [
            c
            for c in calls[:first]
            if c["name"] == "Bash" and EXERCISES.search(c["input"].get("command", ""))
        ]
        print(
            label.group(1),
            label.group(2),
            "calls",
            len(calls),
            "first edit at",
            first,
            "exercised before edit",
            len(ran),
        )


if __name__ == "__main__":
    main()
