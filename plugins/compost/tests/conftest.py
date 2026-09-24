# ABOUTME: Fixtures for compost's tooling: a real upstream git repo served as github.com/acme/skills, a pinned
# ABOUTME: pile.toml, and Jev stand-ins that answer with the SDK's own response models. Scripts import as modules.
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from typesafe_sdk import SystemOneResponse

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pile
from jevtools import core

PLUGIN_ROOT = Path(__file__).parent.parent


def evals_dir() -> Path:
    """The labeled eval cases live in the private compost-evals repo; COMPOST_EVALS points at its evals/."""
    configured = os.environ.get("COMPOST_EVALS")
    if not configured or not Path(configured).expanduser().is_dir():
        pytest.skip("set COMPOST_EVALS to a checkout of compost-evals' evals/ directory to run the live evals")
    return Path(configured).expanduser()


@pytest.fixture(autouse=True)
def private_jev_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "CACHE", tmp_path / "jev-cache.json")
    return tmp_path / "jev-cache.json"


def choice(chosen: str, options, confidence: float = 0.9) -> dict:
    options = list(options)
    rest = (1 - confidence) / max(len(options) - 1, 1)
    probabilities = {option: (confidence if option == chosen else rest) for option in options}
    return {"type": "choice", "choice": chosen, "probabilities": probabilities, "confidence": confidence}


def noul(probability: float) -> dict:
    return {"type": "noul", "noul": probability}


def score(value: float, levels: int = 4) -> dict:
    return {
        "type": "score",
        "score": value,
        "confidence": 0.8,
        "legend": {str(i): f"level {i}" for i in range(levels)},
        "probabilities": {str(i): 1 / levels for i in range(levels)},
    }


def response(answers: dict, input_tokens: int = 100) -> SystemOneResponse:
    payload = {"model": "jev-test", "answers": answers, "usage": {"input_tokens": input_tokens, "output_tokens": 1}}
    return SystemOneResponse.model_validate_json(json.dumps(payload))


class StubClient:
    """Stands in for AsyncTypeSafeClient at the network edge: answers come from `answer(state, questions)`."""

    def __init__(self, answer=None, error: BaseException | None = None):
        self.answer = answer
        self.error = error
        self.calls: list[tuple[dict, dict]] = []

    async def system_one(self, state, questions, model=None):
        self.calls.append((state, questions))
        if self.error:
            raise self.error
        return response(self.answer(state, questions))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class StubJev:
    """Stands in for jevtools.core.Jev in tool tests: `answer(tool, state, questions)` returns plain answer dicts."""

    def __init__(self, answer):
        self.answer = answer
        self.calls: list[tuple[str, dict, dict]] = []

    async def ask(self, tool: str, state: dict, questions: dict) -> dict:
        self.calls.append((tool, state, questions))
        return self.answer(tool, state, questions)


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
