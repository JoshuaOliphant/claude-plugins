#!/usr/bin/env python3
"""
ABOUTME: Fetches public GitHub profile data to enrich resume evidence for skill corroboration.
ABOUTME: Caches results to ~/.claude/resume-tailor/enrichment/github.yaml with configurable staleness.
"""

import argparse
import json
import ssl
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


CACHE_DIR = Path.home() / ".claude" / "resume-tailor" / "enrichment"
CACHE_FILE = CACHE_DIR / "github.yaml"
GITHUB_API = "https://api.github.com"


def fetch_json(url: str, token: str | None = None) -> dict:
    """Fetch JSON from a URL using stdlib urllib."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "resume-tailor-plugin",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    # Create SSL context that works with system certificates
    ctx = ssl.create_default_context()

    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_cache_fresh(max_age_days: int = 7) -> bool:
    """Check if the cached GitHub data is still fresh."""
    if not CACHE_FILE.exists():
        return False

    # Read the cached_at timestamp
    content = CACHE_FILE.read_text(encoding="utf-8")
    for line in content.split("\n"):
        if line.startswith("cached_at:"):
            cached_at = line.split(":", 1)[1].strip()
            try:
                cached_date = datetime.strptime(cached_at, "%Y-%m-%d")
                return datetime.now() - cached_date < timedelta(days=max_age_days)
            except ValueError:
                return False
    return False


def load_cache() -> dict | None:
    """Load cached GitHub data if fresh."""
    if not CACHE_FILE.exists():
        return None

    content = CACHE_FILE.read_text(encoding="utf-8")
    # Simple YAML parser for our flat structure
    data = {}
    current_key = None
    current_list = None

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- ") and current_key:
            if current_list is None:
                current_list = []
            current_list.append(stripped[2:].strip())
            data[current_key] = current_list
            continue

        import re
        match = re.match(r"^([a-z_]+)\s*:\s*(.*)$", stripped)
        if match:
            current_list = None
            key = match.group(1)
            value = match.group(2).strip()
            if value == "":
                current_key = key
                current_list = []
                data[key] = current_list
            elif value.isdigit():
                data[key] = int(value)
                current_key = key
            else:
                data[key] = value
                current_key = key

    return data


def save_cache(data: dict):
    """Save GitHub data to cache file."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    lines = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")

    CACHE_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fetch_github_profile(username: str, token: str | None = None) -> dict:
    """Fetch comprehensive GitHub profile data."""
    # User profile
    user = fetch_json(f"{GITHUB_API}/users/{username}", token)

    # Public repos (sorted by stars)
    repos = fetch_json(f"{GITHUB_API}/users/{username}/repos?sort=stars&per_page=30", token)

    # Aggregate language data
    language_counts = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            language_counts[lang] = language_counts.get(lang, 0) + 1

    # Sort languages by frequency
    sorted_languages = sorted(language_counts.items(), key=lambda x: -x[1])

    # Top repos by stars
    top_repos = []
    for repo in sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:10]:
        top_repos.append({
            "name": repo["name"],
            "description": repo.get("description", ""),
            "stars": repo.get("stargazers_count", 0),
            "language": repo.get("language", ""),
            "forks": repo.get("forks_count", 0),
            "url": repo.get("html_url", ""),
        })

    # Recent activity (repos updated in last 6 months)
    recent_repos = []
    six_months_ago = datetime.now() - timedelta(days=180)
    for repo in repos:
        updated = repo.get("updated_at", "")
        if updated:
            try:
                update_date = datetime.strptime(updated[:10], "%Y-%m-%d")
                if update_date > six_months_ago:
                    recent_repos.append(repo["name"])
            except ValueError:
                pass

    profile_data = {
        "username": username,
        "name": user.get("name", ""),
        "bio": user.get("bio", ""),
        "public_repos": user.get("public_repos", 0),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "primary_languages": [lang for lang, _ in sorted_languages[:8]],
        "language_distribution": {lang: count for lang, count in sorted_languages},
        "top_repos": top_repos,
        "recently_active_repos": recent_repos[:10],
        "profile_url": user.get("html_url", ""),
        "cached_at": datetime.now().strftime("%Y-%m-%d"),
    }

    return profile_data


def format_for_cache(data: dict) -> dict:
    """Flatten the profile data for simple YAML storage."""
    flat = {
        "username": data["username"],
        "name": data.get("name", ""),
        "bio": data.get("bio", ""),
        "public_repos": data["public_repos"],
        "followers": data["followers"],
        "primary_languages": data["primary_languages"],
        "cached_at": data["cached_at"],
    }

    # Top repos as simple list
    flat["top_repos"] = [
        f"{r['name']} ({r['language']}, {r['stars']} stars)" for r in data["top_repos"]
    ]

    flat["recently_active"] = data["recently_active_repos"]

    return flat


def enrich_github(username: str, token: str | None = None, max_age: int = 7) -> dict:
    """Main function: fetch or use cached GitHub data."""
    # Check cache first
    if is_cache_fresh(max_age):
        cached = load_cache()
        if cached and cached.get("username") == username:
            cached["_source"] = "cache"
            return cached

    # Fetch fresh data
    try:
        profile = fetch_github_profile(username, token)
        flat_data = format_for_cache(profile)
        save_cache(flat_data)

        # Return full data for the agent
        profile["_source"] = "api"
        return profile
    except urllib.error.HTTPError as e:
        return {
            "error": f"GitHub API error: {e.code} {e.reason}",
            "username": username,
        }
    except urllib.error.URLError as e:
        return {
            "error": f"Network error: {e.reason}",
            "username": username,
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "username": username,
        }


def main():
    parser = argparse.ArgumentParser(description="Enrich resume with GitHub profile data")
    parser.add_argument("--username", required=True, help="GitHub username")
    parser.add_argument("--token", default=None, help="GitHub personal access token (optional)")
    parser.add_argument("--max-age", type=int, default=7, help="Max cache age in days (default: 7)")
    args = parser.parse_args()

    result = enrich_github(args.username, args.token, args.max_age)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
