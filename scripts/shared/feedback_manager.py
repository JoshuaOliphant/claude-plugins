#!/usr/bin/env python3
"""
ABOUTME: Generic feedback manager for Claude Code plugins.
ABOUTME: Persists user feedback as YAML entries in ~/.claude/{plugin-name}/feedback.yaml.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


def get_feedback_file(plugin_name: str) -> Path:
    """Return the feedback file path for a given plugin."""
    feedback_dir = Path.home() / ".claude" / plugin_name
    feedback_dir.mkdir(parents=True, exist_ok=True)
    return feedback_dir / "feedback.yaml"


def load_feedback_entries(plugin_name: str) -> list:
    """Load all feedback entries from the feedback file."""
    feedback_file = get_feedback_file(plugin_name)
    if not feedback_file.exists():
        return []

    entries = []
    current_entry = {}
    content = feedback_file.read_text(encoding="utf-8")

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped == "---":
            if current_entry:
                entries.append(current_entry)
            current_entry = {}
            continue
        if not stripped:
            continue
        match = re.match(r"^([a-z_]+)\s*:\s*(.+)$", stripped)
        if match:
            current_entry[match.group(1)] = match.group(2).strip()

    if current_entry:
        entries.append(current_entry)

    return entries


def save_feedback(plugin_name: str, data: dict) -> dict:
    """Append a feedback entry to the feedback file.

    Expected fields:
    - category: plugin-specific category or "general"
    - feedback: the actual feedback text
    - context: optional context when the feedback was given
    """
    feedback_file = get_feedback_file(plugin_name)

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "category": data.get("category", "general"),
        "feedback": data.get("feedback", ""),
    }
    if data.get("context"):
        entry["context"] = data["context"]

    # Append to feedback file (entries separated by ---)
    lines = ["---"]
    for key, value in entry.items():
        lines.append(f"{key}: {value}")
    lines.append("")

    mode = "a" if feedback_file.exists() else "w"
    with open(feedback_file, mode, encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return {"status": "saved", "entry": entry, "total_feedback": len(load_feedback_entries(plugin_name))}


def show_feedback(plugin_name: str) -> dict:
    """Show all stored feedback entries."""
    entries = load_feedback_entries(plugin_name)

    # Group by category
    by_category = {}
    for entry in entries:
        cat = entry.get("category", "general")
        by_category.setdefault(cat, []).append(entry)

    return {
        "plugin": plugin_name,
        "total_entries": len(entries),
        "by_category": by_category,
        "feedback": entries,
    }


def clear_feedback(plugin_name: str, category: str | None = None) -> dict:
    """Clear feedback entries, optionally filtering by category."""
    feedback_file = get_feedback_file(plugin_name)

    if category is None:
        # Clear all
        if feedback_file.exists():
            feedback_file.unlink()
        return {"status": "cleared", "scope": "all"}

    # Clear only entries matching category
    entries = load_feedback_entries(plugin_name)
    remaining = [e for e in entries if e.get("category") != category]

    if feedback_file.exists():
        feedback_file.unlink()

    for entry in remaining:
        save_feedback(plugin_name, entry)

    removed = len(entries) - len(remaining)
    return {"status": "cleared", "scope": category, "removed": removed, "remaining": len(remaining)}


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            "error": "Usage: feedback_manager.py <plugin-name> <command> [args]",
            "commands": ["save-feedback", "show-feedback", "clear-feedback"],
            "example": "echo '{\"category\": \"general\", \"feedback\": \"...\"}' | python feedback_manager.py my-plugin save-feedback",
        }))
        sys.exit(1)

    plugin_name = sys.argv[1]
    command = sys.argv[2]

    if command == "save-feedback":
        if len(sys.argv) > 3:
            data = json.loads(sys.argv[3])
        else:
            data = json.loads(sys.stdin.read())
        result = save_feedback(plugin_name, data)
    elif command == "show-feedback":
        result = show_feedback(plugin_name)
    elif command == "clear-feedback":
        category = sys.argv[3] if len(sys.argv) > 3 else None
        result = clear_feedback(plugin_name, category)
    else:
        result = {"error": f"Unknown command: {command}"}

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
