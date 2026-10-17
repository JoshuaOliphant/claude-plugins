# ABOUTME: The one door to TypeSafe Jev for compost's tools: key lookup, a content-hash cache, and bounded concurrency.
# ABOUTME: Tools call Jev.ask(tool, state, questions) and read the Answers view, or get Unavailable; SDK types stay here.
import asyncio
import hashlib
import json
import os
import subprocess
import tempfile
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from typesafe_sdk import AsyncTypeSafeClient, Choice, TypeSafeError

from jevtools.registry import BadInput

MODEL = "jev-latest"
ENV_VAR = "TYPESAFE_API_KEY"
KEYCHAIN_SERVICE = "typesafe"
CACHE = Path.home() / ".cache" / "compost" / "jev-cache.json"
# The most options one Choice may carry. typesafe-sdk 0.7.1 does not encode the API's cap, so this is the
# lower of the two values compost has used (250 and 254); see the ruling on issue #105.
CHOICE_LIMIT = 250


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
        try:
            self.entries: dict[str, dict] = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            self.entries = {}

    def get(self, key: str) -> dict | None:
        return self.entries.get(key)

    def put(self, key: str, answers: dict) -> None:
        self.entries[key] = answers

    def save(self) -> None:
        """Writes a temp file and renames it, since the Stop hook saves from parallel sessions."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=self.path.parent, delete=False, suffix=".tmp") as handle:
            handle.write(json.dumps(self.entries))
        os.replace(handle.name, self.path)


class Answers:
    """Jev's answers to one ask, read by question name. The SDK's answer dicts stay behind this view and in the cache."""

    def __init__(self, raw: dict[str, dict]):
        self.raw = raw

    def noul(self, name: str) -> float:
        return self.raw[name]["noul"]

    def score(self, name: str) -> float:
        return self.raw[name]["score"]

    def confidence(self, name: str) -> float:
        return self.raw[name]["confidence"]

    def choice(self, name: str) -> str:
        """The option a Choice picked."""
        return self.raw[name]["choice"]

    def probabilities(self, name: str) -> dict[str, float]:
        """A Choice's or Score's probability per option, in the order the question listed them."""
        return self.raw[name]["probabilities"]

    def ranked(self, name: str, count: int | None = None) -> list[tuple[str, float]]:
        """A Choice's or Score's options, likeliest first; ties keep the order the question listed them in."""
        return sorted(self.probabilities(name).items(), key=lambda item: -item[1])[:count]


class Jev:
    def __init__(self, client, cache: Cache, concurrency: int = 8):
        self.client = client
        self.cache = cache
        self.semaphore = asyncio.Semaphore(concurrency)
        self.input_tokens = 0
        self.cached = 0

    async def ask(self, tool: str, state: dict, questions: dict) -> Answers:
        key = cache_key(tool, state, questions)
        if (hit := self.cache.get(key)) is not None and questions.keys() <= hit.keys():
            self.cached += 1
            return Answers(hit)
        async with self.semaphore:
            try:
                response = await self.client.system_one(state=state, questions=questions, model=MODEL)
            except (TypeSafeError, OSError) as error:
                raise Unavailable(f"Jev request failed: {error}") from error
        answers = {name: answer.model_dump(mode="json") for name, answer in response.answers.items()}
        self.input_tokens += response.usage.input_tokens
        missing = [name for name in questions if name not in answers]
        if missing:
            raise Unavailable(f"Jev returned no answer for {', '.join(missing)}")
        self.cache.put(key, answers)
        return Answers(answers)


MISSING_KEY = (
    f"{ENV_VAR} is not set and no Keychain item '{KEYCHAIN_SERVICE}' exists; get a key at "
    f"https://docs.typesafe.ai, then store it with: security add-generic-password -s {KEYCHAIN_SERVICE} "
    f'-a "$USER" -w  (or export {ENV_VAR} where the Keychain is unavailable)'
)


def open_client() -> AsyncTypeSafeClient:
    key = resolve_key()
    if key is None:
        raise Unavailable(MISSING_KEY)
    return AsyncTypeSafeClient(api_key=key)


@asynccontextmanager
async def session(client_factory=open_client, cache: Cache | None = None, concurrency: int = 8) -> AsyncIterator[Jev]:
    cache = cache or Cache()
    async with client_factory() as client:
        yield Jev(client, cache, concurrency)
    cache.save()


def parts(options: list[str]) -> list[list[str]]:
    """`options` in runs of at most CHOICE_LIMIT, in order."""
    return [options[index : index + CHOICE_LIMIT] for index in range(0, len(options), CHOICE_LIMIT)]


async def narrow(
    jev,
    tool: str,
    state: dict,
    groups: dict[str, list[str]],
    question: Callable[[dict[str, list[str]]], Choice],
    keep: int = 1,
    also: dict | None = None,
) -> tuple[list[str], Answers | None]:
    """Choose among more options than one Choice can carry, in two stages.

    When every option fits under CHOICE_LIMIT, returns them all and asks nothing. Otherwise asks
    `question(groups)` as "group" (with any `also` questions) and returns the options of the `keep`
    likeliest groups that fit under the cap together, with the answers. A group past the cap is split
    into parts first, so every option stays reachable; options two stages cannot reach are a BadInput.
    """
    options = [option for members in groups.values() for option in members]
    if len(options) <= CHOICE_LIMIT:
        return options, None
    split: dict[str, list[str]] = {}
    for label, members in groups.items():
        pieces = parts(members)
        if len(pieces) == 1:
            split[label] = members
        else:
            split.update({f"{label} (part {i} of {len(pieces)})": piece for i, piece in enumerate(pieces, 1)})
    if len(split) > CHOICE_LIMIT:
        raise BadInput(
            f"{len(options)} options in {len(split)} groups; at most {CHOICE_LIMIT} groups of {CHOICE_LIMIT} "
            "can be chosen among, so narrow the input"
        )
    answers = await jev.ask(tool, state, {"group": question(split), **(also or {})})
    kept: list[str] = []
    for label, _ in answers.ranked("group", keep):
        if kept and len(kept) + len(split[label]) > CHOICE_LIMIT:
            break
        kept += split[label]
    return kept, answers
