# ABOUTME: Jev tools for fitting tests into a suite: find-test (where an acceptance criterion's test belongs).
# ABOUTME: Code lists the candidate tests; Jev picks among them; thresholds below decide extend vs add beside.
import asyncio
from pathlib import Path

from typesafe_sdk import Choice, Noul

from jevtools import suite
from jevtools.core import top
from jevtools.registry import BadInput, tool

CHOICE_LIMIT = 254
FILES_SHORTLIST = 3
EXTEND_COVERED = 0.6
EXTEND_CONFIDENCE = 0.85


def criteria_of(payload: dict) -> list[str]:
    criteria = payload.get("criteria") or ([payload["criterion"]] if "criterion" in payload else [])
    if not criteria:
        raise BadInput("input needs `criterion` or `criteria`")
    return criteria


def gather_suite(payload: dict) -> dict:
    repo = Path(payload.get("repo", "."))
    tests = suite.collect(repo)
    if not tests:
        raise BadInput(f"no tests found under {repo}")
    return {"criteria": criteria_of(payload), "tests": tests}


def neighbour_question(tests: dict[str, str]) -> Choice:
    return Choice(
        instructions=(
            "`criterion` is an acceptance criterion a developer must now cover with a test. Each option is an "
            "existing test in the suite, shown with its source. Which existing test is the best place to cover "
            "the criterion: the test that already exercises this behavior, or else the one whose setup and "
            "subject are closest, so a new case sits beside it?"
        ),
        criteria=tests,
    )


def file_question(files: dict[str, str]) -> Choice:
    return Choice(
        instructions=(
            "`criterion` is an acceptance criterion a developer must now cover with a test. Each option is a test "
            "file, described by the names of its tests. Which file most likely holds the test that exercises this "
            "behavior, or the tests closest to it?"
        ),
        criteria=files,
    )


COVERED = Noul(
    instructions=(
        "Does some existing test in `suite` already exercise the behavior `criterion` describes, so the developer "
        "should change or extend that test rather than write a separate one?"
    )
)


async def shortlist(jev, criterion: str, tests: dict[str, str]) -> dict[str, str]:
    if len(tests) <= CHOICE_LIMIT:
        return tests
    by_file: dict[str, list[str]] = {}
    for node in tests:
        by_file.setdefault(node.split("::")[0], []).append(node.split("::", 1)[1])
    files = {name: ", ".join(names) for name, names in list(by_file.items())[:CHOICE_LIMIT]}
    answers = await jev.ask("find-test/file", {"criterion": criterion}, {"file": file_question(files)})
    chosen = {name for name, _ in top(answers["file"]["probabilities"], FILES_SHORTLIST)}
    narrowed = {node: source for node, source in tests.items() if node.split("::")[0] in chosen}
    return dict(list(narrowed.items())[:CHOICE_LIMIT])


async def place(jev, criterion: str, tests: dict[str, str]) -> dict:
    candidates = await shortlist(jev, criterion, tests)
    answers = await jev.ask(
        "find-test",
        {"criterion": criterion, "suite": list(candidates)},
        {"neighbour": neighbour_question(candidates), "covered": COVERED},
    )
    ranked = top(answers["neighbour"]["probabilities"])
    best, confidence = ranked[0]
    covered = answers["covered"]["noul"]
    extend = covered >= EXTEND_COVERED and confidence >= EXTEND_CONFIDENCE
    return {
        "criterion": criterion,
        "action": "extend" if extend else "add-beside",
        "test": best,
        "confidence": round(confidence, 3),
        "covered": round(covered, 3),
        "alternatives": [name for name, _ in ranked[1:]],
    }


@tool(
    "find-test",
    "Where each acceptance criterion's test belongs: the test to extend, or the one to sit beside.",
    gather_suite,
)
async def find_test(jev, gathered: dict) -> dict:
    placements = await asyncio.gather(*(place(jev, c, gathered["tests"]) for c in gathered["criteria"]))
    return {"placements": list(placements)}
