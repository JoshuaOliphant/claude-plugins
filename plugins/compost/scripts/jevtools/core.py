# ABOUTME: The one door to TypeSafe Jev for compost's tools: key lookup, a content-hash cache, and bounded concurrency.
# ABOUTME: Tools call Jev.ask(state, questions) and get plain dicts back; SDK types stay inside this module.
import asyncio
import hashlib
import json
import os
import subprocess
from pathlib import Path

from typesafe_sdk import AsyncTypeSafeClient, TypeSafeError

MODEL = "jev-latest"
ENV_VAR = "TYPESAFE_API_KEY"
KEYCHAIN_SERVICE = "typesafe"
CACHE = Path.home() / ".cache" / "compost" / "jev-cache.json"


class Unavailable(Exception):
    """Jev cannot answer (no key, or the API failed); callers fall back to their own judgment."""


def resolve_key() -> str | None:
    if os.environ.get(ENV_VAR):
        return os.environ[ENV_VAR]
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    key = result.stdout.strip()
    return key if result.returncode == 0 and key else None


def cache_key(tool: str, state: dict, questions: dict) -> str:
    described = {name: question.model_dump(mode="json") for name, question in questions.items()}
    payload = json.dumps([MODEL, tool, state, described], sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


class Cache:
    def __init__(self, path: Path | None = None):
        self.path = path or CACHE
        self.entries: dict[str, dict] = json.loads(self.path.read_text()) if self.path.exists() else {}

    def get(self, key: str) -> dict | None:
        return self.entries.get(key)

    def put(self, key: str, answers: dict) -> None:
        self.entries[key] = answers

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries))


class Jev:
    def __init__(self, client, cache: Cache, concurrency: int = 8):
        self.client = client
        self.cache = cache
        self.semaphore = asyncio.Semaphore(concurrency)
        self.input_tokens = 0
        self.cached = 0

    async def ask(self, tool: str, state: dict, questions: dict) -> dict:
        key = cache_key(tool, state, questions)
        if (hit := self.cache.get(key)) is not None:
            self.cached += 1
            return hit
        async with self.semaphore:
            try:
                response = await self.client.system_one(state=state, questions=questions, model=MODEL)
            except (TypeSafeError, OSError) as error:
                raise Unavailable(f"Jev request failed: {error}") from error
        answers = {name: answer.model_dump(mode="json") for name, answer in response.answers.items()}
        self.input_tokens += response.usage.input_tokens
        self.cache.put(key, answers)
        return answers


def open_client() -> AsyncTypeSafeClient:
    key = resolve_key()
    if key is None:
        raise Unavailable(
            f"{ENV_VAR} is not set and no Keychain item '{KEYCHAIN_SERVICE}' exists; "
            f'store one with: security add-generic-password -s {KEYCHAIN_SERVICE} -a "$USER" -w'
        )
    return AsyncTypeSafeClient(api_key=key)


def top(probabilities: dict[str, float], count: int = 3) -> list[tuple[str, float]]:
    return sorted(probabilities.items(), key=lambda item: -item[1])[:count]
