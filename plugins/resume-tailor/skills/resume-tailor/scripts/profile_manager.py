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
FEEDBACK_FILE = PROFILE_DIR / "feedback.yaml"
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

    # Load feedback
    feedback = []
    if FEEDBACK_FILE.exists():
        feedback = load_feedback_entries()

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
        "feedback": feedback,
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


def load_feedback_entries() -> list:
    """Load all feedback entries from the feedback file."""
    if not FEEDBACK_FILE.exists():
        return []

    entries = []
    current_entry = {}
    content = FEEDBACK_FILE.read_text(encoding="utf-8")

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


def save_feedback(data: dict):
    """Append a feedback entry to the feedback file.

    Expected fields:
    - category: section name (summary, experience, skills, etc.) or "general"
    - feedback: the actual feedback text
    - context: optional job/company context when the feedback was given
    """
    ensure_dirs()

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

    mode = "a" if FEEDBACK_FILE.exists() else "w"
    with open(FEEDBACK_FILE, mode, encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return {"status": "saved", "entry": entry, "total_feedback": len(load_feedback_entries())}


def show_feedback() -> dict:
    """Show all stored feedback entries."""
    entries = load_feedback_entries()
    return {
        "total_entries": len(entries),
        "feedback": entries,
    }


def clear_feedback(category: str | None = None) -> dict:
    """Clear feedback entries, optionally filtering by category."""
    if category is None:
        # Clear all
        if FEEDBACK_FILE.exists():
            FEEDBACK_FILE.unlink()
        return {"status": "cleared", "scope": "all"}

    # Clear only entries matching category
    entries = load_feedback_entries()
    remaining = [e for e in entries if e.get("category") != category]

    if remaining:
        FEEDBACK_FILE.unlink()
        for entry in remaining:
            save_feedback(entry)
    elif FEEDBACK_FILE.exists():
        FEEDBACK_FILE.unlink()

    removed = len(entries) - len(remaining)
    return {"status": "cleared", "scope": category, "removed": removed, "remaining": len(remaining)}


def set_master_path(directory: str) -> dict:
    """Set the master resume directory in profile.yaml."""
    ensure_dirs()

    dir_path = Path(directory).expanduser().resolve()
    if not dir_path.exists():
        return {"error": f"Directory does not exist: {dir_path}"}

    md_file = dir_path / "master-resume.md"
    if not md_file.exists():
        return {"error": f"No master-resume.md found in {dir_path}"}

    existing = {}
    if PROFILE_FILE.exists():
        existing = parse_simple_yaml(PROFILE_FILE.read_text(encoding="utf-8"))

    existing["master_resume_dir"] = str(dir_path)
    existing["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    write_simple_yaml(existing, PROFILE_FILE)

    return {
        "status": "saved",
        "master_resume_dir": str(dir_path),
        "master_resume_md": str(md_file),
        "master_resume_yaml": str(dir_path / "master-resume.yaml"),
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: profile_manager.py <command> [args]",
            "commands": [
                "load", "save", "save-history", "show-history",
                "update-preferences", "save-feedback", "show-feedback", "clear-feedback",
                "set-master-path",
            ],
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
    elif command == "save-feedback":
        if len(sys.argv) > 2:
            data = json.loads(sys.argv[2])
        else:
            data = json.loads(sys.stdin.read())
        result = save_feedback(data)
    elif command == "show-feedback":
        result = show_feedback()
    elif command == "clear-feedback":
        category = sys.argv[2] if len(sys.argv) > 2 else None
        result = clear_feedback(category)
    elif command == "set-master-path":
        if len(sys.argv) < 3:
            result = {"error": "Usage: profile_manager.py set-master-path <directory>"}
        else:
            result = set_master_path(sys.argv[2])
    else:
        result = {"error": f"Unknown command: {command}"}

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
