#!/usr/bin/env python3
"""
ABOUTME: Fetches current GitHub profile state for comparison and update planning.
ABOUTME: Returns API fields, current README content, repo activity, and pinned repos.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROFILE_REPO_PATH = Path.home() / "Dropbox" / "python_workspace" / "JoshuaOliphant"


def run_gh(args: list[str]) -> dict | list | str | None:
    """Run a gh CLI command and return parsed JSON output."""
    try:
        result = subprocess.run(
            ["gh", "api", *args],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def get_api_fields(username: str) -> dict:
    """Fetch current GitHub API profile fields."""
    user = run_gh([f"users/{username}"])
    if not user:
        return {"error": "Failed to fetch user profile"}

    return {
        "name": user.get("name"),
        "bio": user.get("bio"),
        "company": user.get("company"),
        "location": user.get("location"),
        "blog": user.get("blog"),
        "hireable": user.get("hireable"),
        "twitter_username": user.get("twitter_username"),
        "public_email": user.get("email"),
        "public_repos": user.get("public_repos"),
        "followers": user.get("followers"),
        "following": user.get("following"),
    }


def get_current_readme() -> str | None:
    """Read the current README from the local profile repo."""
    readme_path = PROFILE_REPO_PATH / "README.md"
    if readme_path.exists():
        return readme_path.read_text(encoding="utf-8")
    return None


def get_repos(username: str) -> list[dict]:
    """Fetch non-fork repos sorted by recent push, with key metadata."""
    repos = run_gh([
        f"users/{username}/repos",
        "--paginate",
        "-q", '.[] | select(.fork == false) | {name, description, language, stargazers_count, pushed_at, html_url, topics}',
    ])

    # gh api with -q returns newline-delimited JSON objects
    if repos is None:
        # Try without jq filter and process in Python
        raw = run_gh([f"users/{username}/repos?per_page=100&sort=pushed"])
        if not raw:
            return []
        repos_list = []
        for repo in raw:
            if repo.get("fork"):
                continue
            repos_list.append({
                "name": repo["name"],
                "description": repo.get("description", ""),
                "language": repo.get("language"),
                "stars": repo.get("stargazers_count", 0),
                "pushed_at": repo.get("pushed_at", ""),
                "url": repo.get("html_url", ""),
                "topics": repo.get("topics", []),
            })
        return sorted(repos_list, key=lambda r: r.get("pushed_at", ""), reverse=True)

    if isinstance(repos, list):
        return sorted(repos, key=lambda r: r.get("pushed_at", ""), reverse=True)
    return []


def get_pinned_repos(username: str) -> list[dict]:
    """Fetch pinned repos via GraphQL."""
    query = """
    query($username: String!) {
      user(login: $username) {
        pinnedItems(first: 6, types: REPOSITORY) {
          nodes {
            ... on Repository {
              name
              description
              stargazerCount
              primaryLanguage { name }
              url
            }
          }
        }
      }
    }
    """
    try:
        result = subprocess.run(
            ["gh", "api", "graphql",
             "-f", f"query={query}",
             "-f", f"username={username}"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        nodes = data.get("data", {}).get("user", {}).get("pinnedItems", {}).get("nodes", [])
        return [
            {
                "name": n["name"],
                "description": n.get("description", ""),
                "stars": n.get("stargazerCount", 0),
                "language": (n.get("primaryLanguage") or {}).get("name"),
                "url": n.get("url", ""),
            }
            for n in nodes
        ]
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def main():
    parser = argparse.ArgumentParser(description="Fetch current GitHub profile state")
    parser.add_argument("--username", required=True, help="GitHub username")
    args = parser.parse_args()

    state = {
        "username": args.username,
        "api_fields": get_api_fields(args.username),
        "current_readme": get_current_readme(),
        "repos": get_repos(args.username),
        "pinned_repos": get_pinned_repos(args.username),
        "profile_repo_path": str(PROFILE_REPO_PATH),
    }

    print(json.dumps(state, indent=2, default=str))


if __name__ == "__main__":
    main()
