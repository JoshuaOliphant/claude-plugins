# ABOUTME: Fixtures for compost's tooling: a real upstream git repo reachable as github.com/acme/skills,
# ABOUTME: and a pile.toml pinned to its first commit. Bundled scripts are importable as top-level modules.
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pile

PLUGIN_ROOT = Path(__file__).parent.parent


def run_git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def commit(repo: Path, files: dict[str, str], message: str) -> str:
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", message)
    return run_git(repo, "rev-parse", "HEAD")


@pytest.fixture
def upstream(tmp_path, monkeypatch) -> Path:
    """acme/skills on a fake github.com: git rewrites https://github.com/ to a local directory."""
    github = tmp_path / "github"
    repo = github / "acme" / "skills.git"
    repo.mkdir(parents=True)
    run_git(repo, "init", "-q", "-b", "main")
    run_git(repo, "config", "user.email", "t@example.com")
    run_git(repo, "config", "user.name", "Tester")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", f"url.{github}/.insteadOf")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "https://github.com/")
    monkeypatch.setattr(pile, "CLONES", tmp_path / "clones")
    commit(repo, {"skills/to-spec/SKILL.md": "spec v1\n", "README.md": "readme\n"}, "first")
    return repo


@pytest.fixture
def pile_file(tmp_path, upstream) -> Path:
    first = run_git(upstream, "rev-parse", "HEAD")
    path = tmp_path / "pile.toml"
    path.write_text(f'''[[source]]
name = "acme"
repo = "acme/skills"
role = "input"
license = "MIT"
pin = "{first}"
feeds = {{ "skills/to-spec" = ["spec"], "skills/to-tickets" = ["slice", "spec"] }}

[[source]]
name = "own"
repo = "me/old-plugins"
role = "frozen"
license = "MIT"
pin = "aaaaaaaaaaaaaaaa"

[[source]]
name = "watch"
repo = "else/skills"
role = "reference"
license = "Apache-2.0"
pin = "bbbbbbbbbbbbbbbb"
''')
    return path
