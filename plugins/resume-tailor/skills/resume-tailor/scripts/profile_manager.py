#!/usr/bin/env python3
"""
ABOUTME: Manages persistent user profile data for resume tailoring across sessions.
ABOUTME: Handles profile load/save, customization history, and user preferences at ~/.claude/resume-tailor/.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


PROFILE_DIR = Path.home() / ".claude" / "resume-tailor"
PROFILE_FILE = PROFILE_DIR / "profile.yaml"
PREFERENCES_FILE = PROFILE_DIR / "preferences.yaml"
HISTORY_DIR = PROFILE_DIR / "history"
ENRICHMENT_DIR = PROFILE_DIR / "enrichment"


def ensure_dirs():
    """Create the profile directory structure on first use."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(exist_ok=True)
    ENRICHMENT_DIR.mkdir(exist_ok=True)


def parse_simple_yaml(text: str) -> dict:
    """Parse a simple flat YAML file (key: value pairs, no nesting beyond lists)."""
    result = {}
    current_key = None
    current_list = None

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # List item
        if stripped.startswith("- ") and current_key:
            if current_list is None:
                current_list = []
            current_list.append(stripped[2:].strip())
            result[current_key] = current_list
            continue

        # Key-value pair
        match = re.match(r"^([a-z_]+)\s*:\s*(.*)$", stripped)
        if match:
            # Save previous list if any
            if current_list is not None:
                current_list = None

            key = match.group(1)
            value = match.group(2).strip()

            if value == "":
                # Next lines might be a list
                current_key = key
                current_list = []
                result[key] = current_list
            elif value.startswith("[") and value.endswith("]"):
                # Inline list
                items = [item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()]
                result[key] = items
                current_key = key
                current_list = None
            elif value.lower() in ("true", "false"):
                result[key] = value.lower() == "true"
                current_key = key
                current_list = None
            elif value.isdigit():
                result[key] = int(value)
                current_key = key
                current_list = None
            else:
                result[key] = value.strip("'\"")
                current_key = key
                current_list = None
        else:
            current_key = None
            current_list = None

    return result


def write_simple_yaml(data: dict, filepath: Path):
    """Write a simple flat YAML file."""
    lines = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {value}")

    filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_profile() -> dict:
    """Load the user profile and all associated data."""
    ensure_dirs()

    profile = {}
    if PROFILE_FILE.exists():
        profile = parse_simple_yaml(PROFILE_FILE.read_text(encoding="utf-8"))

    preferences = {}
    if PREFERENCES_FILE.exists():
        preferences = parse_simple_yaml(PREFERENCES_FILE.read_text(encoding="utf-8"))

    # Load enrichment cache
    enrichment = {}
    github_file = ENRICHMENT_DIR / "github.yaml"
    if github_file.exists():
        enrichment["github"] = parse_simple_yaml(github_file.read_text(encoding="utf-8"))

    portfolio_file = ENRICHMENT_DIR / "portfolio.yaml"
    if portfolio_file.exists():
        enrichment["portfolio"] = parse_simple_yaml(portfolio_file.read_text(encoding="utf-8"))

    # Load recent history (last 5 entries)
    history = []
    if HISTORY_DIR.exists():
        history_files = sorted(HISTORY_DIR.glob("*.yaml"), reverse=True)[:5]
        for hf in history_files:
            history.append(parse_simple_yaml(hf.read_text(encoding="utf-8")))

    result = {
        "profile": profile,
        "preferences": preferences,
        "enrichment": enrichment,
        "recent_history": history,
        "is_new_user": not PROFILE_FILE.exists(),
        "profile_dir": str(PROFILE_DIR),
    }
    return result


def save_profile(data: dict):
    """Save/update the user profile."""
    ensure_dirs()

    # Merge with existing profile
    existing = {}
    if PROFILE_FILE.exists():
        existing = parse_simple_yaml(PROFILE_FILE.read_text(encoding="utf-8"))

    existing.update(data)
    existing["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    # Track customization count
    if "customization_count" not in existing:
        existing["customization_count"] = 0

    write_simple_yaml(existing, PROFILE_FILE)
    return {"status": "saved", "profile": existing}


def save_history(data: dict):
    """Save a customization history record."""
    ensure_dirs()

    # Generate filename from date and job info
    date_str = datetime.now().strftime("%Y-%m-%d")
    title_slug = re.sub(r"[^a-z0-9]+", "-", data.get("job_title", "unknown").lower())[:30]
    company_slug = re.sub(r"[^a-z0-9]+", "-", data.get("company", "unknown").lower())[:20]
    filename = f"{date_str}_{title_slug}_{company_slug}.yaml"

    history_file = HISTORY_DIR / filename
    data["date"] = date_str
    write_simple_yaml(data, history_file)

    # Increment customization count in profile
    if PROFILE_FILE.exists():
        profile = parse_simple_yaml(PROFILE_FILE.read_text(encoding="utf-8"))
        profile["customization_count"] = profile.get("customization_count", 0) + 1
        write_simple_yaml(profile, PROFILE_FILE)

    return {"status": "saved", "file": str(history_file)}


def show_history() -> dict:
    """List all customization history."""
    ensure_dirs()

    history = []
    if HISTORY_DIR.exists():
        history_files = sorted(HISTORY_DIR.glob("*.yaml"), reverse=True)
        for hf in history_files:
            entry = parse_simple_yaml(hf.read_text(encoding="utf-8"))
            entry["_file"] = hf.name
            history.append(entry)

    return {
        "total_customizations": len(history),
        "history": history,
    }


def update_preferences(data: dict):
    """Update user preferences."""
    ensure_dirs()

    existing = {}
    if PREFERENCES_FILE.exists():
        existing = parse_simple_yaml(PREFERENCES_FILE.read_text(encoding="utf-8"))

    existing.update(data)
    write_simple_yaml(existing, PREFERENCES_FILE)
    return {"status": "saved", "preferences": existing}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: profile_manager.py <command> [args]",
            "commands": ["load", "save", "save-history", "show-history", "update-preferences"],
        }))
        sys.exit(1)

    command = sys.argv[1]

    if command == "load":
        result = load_profile()
    elif command == "save":
        # Read JSON data from stdin or remaining args
        if len(sys.argv) > 2:
            data = json.loads(sys.argv[2])
        else:
            data = json.loads(sys.stdin.read())
        result = save_profile(data)
    elif command == "save-history":
        if len(sys.argv) > 2:
            data = json.loads(sys.argv[2])
        else:
            data = json.loads(sys.stdin.read())
        result = save_history(data)
    elif command == "show-history":
        result = show_history()
    elif command == "update-preferences":
        if len(sys.argv) > 2:
            data = json.loads(sys.argv[2])
        else:
            data = json.loads(sys.stdin.read())
        result = update_preferences(data)
    else:
        result = {"error": f"Unknown command: {command}"}

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
