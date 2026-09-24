# ABOUTME: Jev tools for fitting tests into a suite and proving them: find-test, duplicate-test, ac-exercised,
# ABOUTME: test-value, and claim-backed. Code gathers the candidates; Jev picks or checks; thresholds below decide.
import ast
import asyncio
import json
import math
import re
from collections import Counter
from pathlib import Path

from typesafe_sdk import Choice, Noul, Score

from jevtools import suite
from jevtools.core import top
from jevtools.registry import BadInput, require, tool

CHOICE_LIMIT = 254
FILES_SHORTLIST = 3
EXTEND_COVERED = 0.7
FULL_SOURCE_CHARS = 4000

NEIGHBOURS = 5
DUPLICATE = 0.5
WORD = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|[0-9]+")

EXERCISED = 0.5

CONTEXT_LINES = 4
EXCLUDE_BELOW = 1.5

BACKED = 0.5
OUTPUT_HEAD = 2000
OUTPUT_TAIL = 8000


def criteria_of(payload: dict) -> list[str]:
    criteria = payload.get("criteria") or ([payload["criterion"]] if "criterion" in payload else [])
    if not criteria:
        raise BadInput("input needs `criterion` or `criteria`")
    return criteria


def gather_suite(payload: dict) -> dict:
    repo = Path(payload.get("repo", "."))
    tests = suite.collect(repo, FULL_SOURCE_CHARS)
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
        "`criterion` is an acceptance criterion a developer must now cover with a test. `test.source` is an "
        "existing test in the suite. Does this test already exercise the behavior `criterion` describes, in one "
        "of its cases or assertions, so the developer should change or extend it rather than write a new test?"
    )
)


async def shortlist(jev, criterion: str, tests: dict[str, str]) -> dict[str, str]:
    if len(tests) <= CHOICE_LIMIT:
        return {node: source[: suite.SOURCE_CHARS] for node, source in tests.items()}
    by_file: dict[str, list[str]] = {}
    for node in tests:
        by_file.setdefault(node.split("::")[0], []).append(node.split("::", 1)[1])
    files = {name: ", ".join(names) for name, names in list(by_file.items())[:CHOICE_LIMIT]}
    answers = await jev.ask("find-test/file", {"criterion": criterion}, {"file": file_question(files)})
    chosen = {name for name, _ in top(answers["file"]["probabilities"], FILES_SHORTLIST)}
    narrowed = {node: source[: suite.SOURCE_CHARS] for node, source in tests.items() if node.split("::")[0] in chosen}
    return dict(list(narrowed.items())[:CHOICE_LIMIT])


async def place(jev, criterion: str, tests: dict[str, str]) -> dict:
    candidates = await shortlist(jev, criterion, tests)
    answers = await jev.ask("find-test", {"criterion": criterion}, {"neighbour": neighbour_question(candidates)})
    ranked = top(answers["neighbour"]["probabilities"])
    best, confidence = ranked[0]
    state = {"criterion": criterion, "test": {"id": best, "source": tests[best]}}
    covered = (await jev.ask("find-test/covered", state, {"covered": COVERED}))["covered"]["noul"]
    return {
        "criterion": criterion,
        "action": "extend" if covered >= EXTEND_COVERED else "add-beside",
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


def tfidf(documents: dict[str, str]) -> dict[str, dict[str, float]]:
    counts = {name: Counter(word.lower() for word in WORD.findall(text)) for name, text in documents.items()}
    spread = Counter(word for words in counts.values() for word in words)
    total = len(documents)
    vectors = {}
    for name, words in counts.items():
        weights = {
            word: (1 + math.log(count)) * (math.log((1 + total) / (1 + spread[word])) + 1)
            for word, count in words.items()
        }
        norm = math.sqrt(sum(weight * weight for weight in weights.values())) or 1.0
        vectors[name] = {word: weight / norm for word, weight in weights.items()}
    return vectors


def nearest(node: str, vectors: dict[str, dict[str, float]], count: int) -> list[tuple[str, float]]:
    mine = vectors[node]
    similarities = [
        (other, sum(weight * vector.get(word, 0.0) for word, weight in mine.items()))
        for other, vector in vectors.items()
        if other != node
    ]
    return sorted(similarities, key=lambda item: -item[1])[:count]


def gather_changes(payload: dict) -> dict:
    require(payload, "base")
    repo = Path(payload.get("repo", "."))
    try:
        before = suite.collect_at(repo, payload["base"], FULL_SOURCE_CHARS)
    except LookupError as error:
        raise BadInput(str(error)) from error
    after = suite.collect(repo, FULL_SOURCE_CHARS)
    vectors = tfidf({node: f"{node}\n{source}" for node, source in after.items()})
    changes = [
        {
            "test": node,
            "status": "changed" if node in before else "added",
            "source": source,
            "neighbours": [
                {"test": other, "source": after[other], "similarity": round(similarity, 3)}
                for other, similarity in nearest(node, vectors, NEIGHBOURS)
            ],
        }
        for node, source in after.items()
        if before.get(node) != source
    ]
    return {"base": payload["base"], "changes": changes}


SAME_BEHAVIOR = Noul(
    instructions=(
        "`added` is a test a developer just added or changed; `existing` is another test in the same suite. Do "
        "the two exercise the same behavior: the same unit, in the same situation, checked for the same outcome, "
        "so that `added` protects nothing `existing` does not already protect and could be folded into it as a "
        "parametrized case or an extra assertion? Tests of the same unit that reach different branches, rules, "
        "or outcomes exercise different behaviors."
    )
)


async def compare(jev, change: dict) -> dict:
    added = {"test": change["test"], "source": change["source"]}

    async def pair(neighbour: dict) -> dict:
        state = {"added": added, "existing": {"test": neighbour["test"], "source": neighbour["source"]}}
        answers = await jev.ask("duplicate-test", state, {"same_behavior": SAME_BEHAVIOR})
        same = answers["same_behavior"]["noul"]
        return {"test": neighbour["test"], "same_behavior": round(same, 3), "similarity": neighbour["similarity"]}

    neighbours = await asyncio.gather(*(pair(n) for n in change["neighbours"]))
    duplicates = sorted((n for n in neighbours if n["same_behavior"] >= DUPLICATE), key=lambda n: -n["same_behavior"])
    return {
        "test": change["test"],
        "status": change["status"],
        "recommendation": f"fold into {duplicates[0]['test']}" if duplicates else "keep",
        "duplicates": duplicates,
        "neighbours": list(neighbours),
    }


@tool(
    "duplicate-test",
    "For each test added or changed since a base ref: the existing tests it re-covers, to fold it into.",
    gather_changes,
)
async def duplicate_test(jev, gathered: dict) -> dict:
    tests = await asyncio.gather(*(compare(jev, change) for change in gathered["changes"]))
    return {"base": gathered["base"], "tests": list(tests)}


def gather_mapped(payload: dict) -> dict:
    criteria = payload.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise BadInput("input needs `criteria`: a list of {id, text, test}")
    for criterion in criteria:
        require(criterion, "id", "text", "test")
    tests = suite.collect(Path(payload.get("repo", ".")), FULL_SOURCE_CHARS)
    return {"criteria": [mapped(criterion, tests) for criterion in criteria]}


def mapped(criterion: dict, tests: dict[str, str]) -> dict:
    function, _, case = criterion["test"].partition("[")
    return {**criterion, "case": case.removesuffix("]") or None, "source": tests.get(function)}


ASSERTS_THEN = Noul(
    instructions=(
        "`criterion` is an acceptance criterion in Given/When/Then form. `test.source` is the test mapped to it. "
        "When `test.case` is set, only the parametrized case with that id is mapped: judge that one row and "
        "ignore the others. Do the test's assertions check the outcome the criterion's Then states, in the "
        "situation its Given and When describe? Answer no when the test runs the code without asserting that "
        "outcome, asserts a different outcome, or sets up a different situation."
    )
)


async def exercise(jev, criterion: dict) -> dict:
    found = {"id": criterion["id"], "test": criterion["test"]}
    if criterion["source"] is None:
        return {**found, "exercised": False, "probability": None, "reason": "no test with this node id"}
    state = {
        "criterion": criterion["text"],
        "test": {"id": criterion["test"], "case": criterion["case"], "source": criterion["source"]},
    }
    answers = await jev.ask("ac-exercised", state, {"asserts_then": ASSERTS_THEN})
    probability = answers["asserts_then"]["noul"]
    return {**found, "exercised": probability >= EXERCISED, "probability": round(probability, 3)}


@tool(
    "ac-exercised",
    "Whether the test mapped to each acceptance criterion actually asserts the criterion's Then.",
    gather_mapped,
)
async def ac_exercised(jev, gathered: dict) -> dict:
    results = await asyncio.gather(*(exercise(jev, c) for c in gathered["criteria"]))
    return {"criteria": list(results), "to_read": [r["id"] for r in results if not r["exercised"]]}


TEST_VALUE_LEVELS = [
    (
        'Covering it proves nothing: an `if __name__ == "__main__":` guard, a constant, a re-export or import, a '
        "debugging repr, or a line that only hands off to a framework or the standard library as documented."
    ),
    (
        "Covering it proves little: a defensive branch for a state the program cannot reach through its callers, "
        "or a pass-through wrapper whose test would only re-test what it wraps."
    ),
    (
        "Covering it proves some behavior: an error message, a fallback, or an edge case a caller can reach, "
        "whose breakage would be noticed at once and cost little."
    ),
    (
        "Covering it guards behavior a user depends on: a decision, calculation, transformation, or side effect, "
        "or the handling of a real bad input, whose silent breakage would ship wrong results."
    ),
]


def blocks_of(lines: list[int], source: list[str]) -> list[tuple[int, int]]:
    blocks: list[list[int]] = []
    for number in sorted(set(lines)):
        if blocks and not any(line.strip() for line in source[blocks[-1][1] : number - 1]):
            blocks[-1][1] = number
        else:
            blocks.append([number, number])
    return [(first, last) for first, last in blocks]


def enclosing(tree: ast.AST | None, line: int, source: list[str]) -> str | None:
    if tree is None:
        return None
    holders = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        and node.lineno <= line <= node.end_lineno
    ]
    return source[max(holders, key=lambda node: node.lineno).lineno - 1].strip() if holders else None


def excerpt(source: list[str], first: int, last: int) -> str:
    start, end = max(first - CONTEXT_LINES, 1), min(last + CONTEXT_LINES, len(source))
    return "\n".join(
        f"{'>>' if first <= number <= last else '  '} {number:4} {source[number - 1]}"
        for number in range(start, end + 1)
    )


def uncovered_of(payload: dict) -> list[dict]:
    if "coverage" in payload:
        try:
            report = json.loads(Path(payload["coverage"]).read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise BadInput(f"cannot read coverage report {payload['coverage']}: {error}") from error
        return [
            {"file": name, "lines": data["missing_lines"]}
            for name, data in report.get("files", {}).items()
            if data["missing_lines"]
        ]
    if isinstance(payload.get("uncovered"), list):
        for item in payload["uncovered"]:
            require(item, "file", "lines")
        return payload["uncovered"]
    raise BadInput("input needs `coverage` (a coverage.json path) or `uncovered` (a list of {file, lines})")


def parsed(text: str, path: Path) -> ast.AST | None:
    if path.suffix != ".py":
        return None
    try:
        return ast.parse(text)
    except SyntaxError:
        return None


def gather_gaps(payload: dict) -> dict:
    repo = Path(payload.get("repo", "."))
    gaps = []
    for item in uncovered_of(payload):
        path = repo / item["file"]
        if not path.is_file():
            raise BadInput(f"no file {path} for uncovered lines")
        text = path.read_text(errors="replace")
        source = text.splitlines()
        tree = parsed(text, path)
        for first, last in blocks_of(item["lines"], source):
            gaps.append(
                {
                    "file": item["file"],
                    "lines": [first, last],
                    "enclosing": enclosing(tree, first, source),
                    "excerpt": excerpt(source, first, last),
                }
            )
    return {"gaps": gaps}


TEST_VALUE = Score(
    instructions=(
        "`excerpt` shows lines of `file` that no test runs, marked `>>`, with their surroundings; `enclosing` is "
        "the definition that holds them. How much would a test that runs the marked lines prove about the "
        "program's behavior?"
    ),
    criteria=TEST_VALUE_LEVELS,
)


async def value(jev, gap: dict) -> dict:
    answer = (await jev.ask("test-value", gap, {"value": TEST_VALUE}))["value"]
    return {
        "file": gap["file"],
        "lines": gap["lines"],
        "decision": "exclude" if answer["score"] < EXCLUDE_BELOW else "test",
        "score": round(answer["score"], 2),
        "probabilities": answer["probabilities"],
    }


@tool(
    "test-value",
    "How much a test covering each uncovered block would prove: propose an exclusion or a test.",
    gather_gaps,
)
async def test_value(jev, gathered: dict) -> dict:
    blocks = await asyncio.gather(*(value(jev, gap) for gap in gathered["gaps"]))
    excluded = [f"{b['file']}:{b['lines'][0]}-{b['lines'][1]}" for b in blocks if b["decision"] == "exclude"]
    return {"blocks": list(blocks), "exclude": excluded}


def clip(output: str) -> str:
    if len(output) <= OUTPUT_HEAD + OUTPUT_TAIL:
        return output
    dropped = len(output) - OUTPUT_HEAD - OUTPUT_TAIL
    return f"{output[:OUTPUT_HEAD]}\n[... {dropped} characters clipped ...]\n{output[-OUTPUT_TAIL:]}"


def output_of(item: dict) -> str:
    if "output" in item:
        return item["output"]
    if "output_file" in item:
        try:
            return Path(item["output_file"]).read_text(errors="replace")
        except OSError as error:
            raise BadInput(f"cannot read {item['output_file']}: {error}") from error
    raise BadInput(f"claim {item['claim']!r} needs `output` or `output_file`")


def gather_claims(payload: dict) -> dict:
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        raise BadInput("input needs `claims`: a list of {claim, output} or {claim, output_file}")
    for item in claims:
        require(item, "claim")
    return {"claims": [{"claim": item["claim"], "output": clip(output_of(item))} for item in claims]}


OUTPUT_BACKS_CLAIM = Noul(
    instructions=(
        "`claim` is a statement from a report about finished work, such as a test count, a coverage figure, or "
        "a clean lint run. `output` is the captured output of the command offered as its evidence; a long output "
        "is clipped in the middle. Does `output` show what `claim` states, with the same numbers? Judge only what "
        "the claim asserts: a failure, warning, or skipped test elsewhere in the output counts against the claim "
        "only when the claim says or implies there was none. An empty output, or one that never shows what the "
        "claim is about, does not back it."
    )
)


async def check_claim(jev, item: dict) -> dict:
    probability = (await jev.ask("claim-backed", item, {"backed": OUTPUT_BACKS_CLAIM}))["backed"]["noul"]
    return {"claim": item["claim"], "backed": probability >= BACKED, "probability": round(probability, 3)}


@tool(
    "claim-backed",
    "Whether the captured command output supports each claim a report makes.",
    gather_claims,
)
async def claim_backed(jev, gathered: dict) -> dict:
    claims = await asyncio.gather(*(check_claim(jev, item) for item in gathered["claims"]))
    return {"claims": list(claims), "unbacked": [c["claim"] for c in claims if not c["backed"]]}
