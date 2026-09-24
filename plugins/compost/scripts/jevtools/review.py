# ABOUTME: Jev tools for review: triage-finding (severity, and whether a skeptic is worth spawning), review-risk
# ABOUTME: (structural risk per changed file), canon-pick (which canon essays a change needs), locate (a claim's line).
import asyncio
import re
import subprocess
from pathlib import Path

from typesafe_sdk import Choice, Noul, NoulCriteria, Score

from jevtools.core import top
from jevtools.registry import BadInput, require, tool

CANON = Path(__file__).resolve().parents[2] / "canon"
HUNK_CHARS = 4000
FILE_DIFF_CHARS = 6000
CHANGE_CHARS = 8000
CHOICE_LIMIT = 250
DOCUMENT_CHARS = 90_000
MAX_PICKS = 3

SKEPTIC_SEVERITY = 0.3
SKEPTIC_CONFIDENCE = 0.25
STRUCTURAL = 2.5
CANON_PICK = 0.15
FOUND = 0.7

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)

SEVERITIES = {
    "blocker": (
        "Wrong behavior, a missing or broken acceptance criterion, data loss, a security hole, a documented rule "
        "broken outright, or a test that passes without proving anything."
    ),
    "major": (
        "A real cost the code will pay later: a leaky interface, a domain term used wrongly, a decision that "
        "contradicts an ADR, an unhandled failure at a boundary, instructions that leave a reader stuck."
    ),
    "minor": "A judgement call worth a sentence: a naming or wording nit, or a smell with no behavior at stake.",
    "not-a-finding": (
        "The claim is wrong or not supported by the hunk, asks for generality nobody needs, or is a style point a "
        "configured linter or formatter already enforces."
    ),
}

RISK_LEVELS = [
    "Cosmetic: formatting, comments, documentation wording, or a rename, with no change in behavior.",
    "Local logic: behavior changes inside existing functions or tests; callers and interfaces are untouched.",
    "New behavior inside one module: new private functions, branches, or cases that other modules do not see.",
    (
        "An interface change: a public function's signature, a CLI, a schema, a config or file format, or an "
        "instruction contract that other code, agents, or users rely on."
    ),
    (
        "New structure: a new module or component boundary, shared or global state, a new external dependency, or "
        "a new data flow between components."
    ),
]

NO_ESSAY = "none"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise BadInput(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def file_diff(repo: Path, base: str, head: str, path: str) -> str:
    return git(repo, "diff", f"{base}...{head}", "--", path)


def hunk_around(diff: str, line: int | None) -> str:
    if line is None:
        return diff[:HUNK_CHARS]
    headers = list(HUNK_HEADER.finditer(diff))
    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(diff)
        first = int(header.group(1))
        count = int(header.group(2)) if header.group(2) is not None else 1
        if first <= line < first + max(count, 1):
            return diff[header.start() : end][:HUNK_CHARS]
    return ""


def gather_findings(payload: dict) -> dict:
    require(payload, "findings")
    findings = payload["findings"]
    if not isinstance(findings, list) or not findings:
        raise BadInput("`findings` must be a non-empty list")
    repo = Path(payload.get("repo", "."))
    base, head = payload.get("base"), payload.get("head", "HEAD")
    diffs: dict[str, str] = {}
    gathered = []
    for finding in findings:
        require(finding, "file", "claim")
        hunk = finding.get("hunk")
        if hunk is None and base:
            if finding["file"] not in diffs:
                diffs[finding["file"]] = file_diff(repo, base, head, finding["file"])
            hunk = hunk_around(diffs[finding["file"]], finding.get("line"))
        gathered.append(
            {
                "file": finding["file"],
                "line": finding.get("line"),
                "claim": finding["claim"],
                "evidence": finding.get("evidence", ""),
                "hunk": hunk or "",
            }
        )
    return {"findings": gathered}


SEVERITY = Choice(
    instructions=(
        "A code reviewer raised `finding` (its `claim` and quoted `evidence`) about a change; `hunk` is the part of "
        "the diff at `finding.file` around `finding.line`, empty when the line is outside the diff. Judging only "
        "from what is shown, how severe is the finding?"
    ),
    criteria=SEVERITIES,
)


def worth_skeptic(probabilities: dict[str, float], confidence: float) -> bool:
    serious = probabilities.get("blocker", 0.0) + probabilities.get("major", 0.0)
    return serious >= SKEPTIC_SEVERITY or confidence < SKEPTIC_CONFIDENCE


async def triage(jev, finding: dict) -> dict:
    state = {
        "finding": {key: finding[key] for key in ("file", "line", "claim", "evidence")},
        "hunk": finding["hunk"],
    }
    answer = (await jev.ask("triage-finding", state, {"severity": SEVERITY}))["severity"]
    probabilities = {name: round(value, 3) for name, value in answer["probabilities"].items()}
    return {
        "file": finding["file"],
        "line": finding["line"],
        "claim": finding["claim"],
        "severity": top(answer["probabilities"], 1)[0][0],
        "confidence": round(answer["confidence"], 3),
        "probabilities": probabilities,
        "worth_skeptic": worth_skeptic(answer["probabilities"], answer["confidence"]),
    }


@tool(
    "triage-finding",
    "Severity of each review finding (blocker, major, minor, not a finding) and whether a skeptic is worth it.",
    gather_findings,
)
async def triage_finding(jev, gathered: dict) -> dict:
    triaged = await asyncio.gather(*(triage(jev, finding) for finding in gathered["findings"]))
    return {"findings": list(triaged), "skeptics": sum(finding["worth_skeptic"] for finding in triaged)}


def changed_files(repo: Path, base: str, head: str) -> dict[str, str]:
    statuses = {"A": "added", "D": "deleted"}
    changed = {}
    for row in git(repo, "diff", "--name-status", "--no-renames", f"{base}...{head}").splitlines():
        status, path = row.split("\t", 1)
        changed[path] = statuses.get(status[0], "modified")
    return changed


def gather_diff(payload: dict) -> dict:
    require(payload, "base")
    repo = Path(payload.get("repo", "."))
    base, head = payload["base"], payload.get("head", "HEAD")
    changed = changed_files(repo, base, head)
    if not changed:
        raise BadInput(f"the diff {base}...{head} is empty")
    return {
        "files": [
            {"file": path, "status": status, "diff": file_diff(repo, base, head, path)[:FILE_DIFF_CHARS]}
            for path, status in changed.items()
        ]
    }


RISK = Score(
    instructions=(
        "`diff` is one file's part of a change under review (`status` says whether the file is new, modified, or "
        "deleted; `changed_files` lists every file in the change). How much structural risk does this file's "
        "change carry: what could it break beyond the lines shown?"
    ),
    criteria=RISK_LEVELS,
)


async def assess(jev, changed: dict, everything: list[str]) -> dict:
    state = {**changed, "changed_files": everything}
    answer = (await jev.ask("review-risk", state, {"risk": RISK}))["risk"]
    return {
        "file": changed["file"],
        "score": round(answer["score"], 2),
        "confidence": round(answer["confidence"], 3),
        "structural": answer["score"] >= STRUCTURAL,
    }


@tool(
    "review-risk",
    "Structural risk of each changed file, ranked, with a flag above the threshold that opens approach fit.",
    gather_diff,
)
async def review_risk(jev, gathered: dict) -> dict:
    everything = [changed["file"] for changed in gathered["files"]]
    assessed = await asyncio.gather(*(assess(jev, changed, everything) for changed in gathered["files"]))
    ranked = sorted(assessed, key=lambda entry: -entry["score"])
    return {"files": ranked, "structural": any(entry["structural"] for entry in ranked)}


def essay_heads(canon: Path) -> dict[str, dict]:
    heads = {}
    for path in sorted(canon.glob("*.md")):
        if path.name == "README.md":
            continue
        lines = path.read_text().splitlines()
        title = lines[0].removeprefix("# ").strip()
        body = "\n".join(lines[1:]).strip()
        heads[path.stem] = {"title": title, "opening": body.split("\n\n", 1)[0].replace("\n", " ")}
    return heads


def change_summary(repo: Path, base: str, head: str) -> str:
    messages = git(repo, "log", "--format=%s%n%b", f"{base}..{head}").strip()
    stat = git(repo, "diff", "--stat", f"{base}...{head}").strip()
    diff = git(repo, "diff", f"{base}...{head}")
    return f"{messages}\n\n{stat}\n\n{diff}"[:CHANGE_CHARS]


def gather_change(payload: dict) -> dict:
    if "summary" in payload:
        summary = payload["summary"]
    elif "base" in payload:
        summary = change_summary(Path(payload.get("repo", ".")), payload["base"], payload.get("head", "HEAD"))
    else:
        raise BadInput("input needs `summary` or `base`")
    essays = essay_heads(Path(payload.get("canon", CANON)))
    if not essays:
        raise BadInput("no canon essays found")
    return {"change": summary, "essays": essays}


def essay_question(essays: dict[str, dict]) -> Choice:
    options = {stem: f"{head['title']}: {head['opening']}" for stem, head in essays.items()}
    options[NO_ESSAY] = "No essay: the change is routine and none of these principles is at stake."
    return Choice(
        instructions=(
            "`change` summarizes a code change about to be reviewed. Each option is a short essay on an engineering "
            "principle. Which essay's warning is most at stake in this change, the one a reviewer should read first?"
        ),
        criteria=options,
    )


@tool(
    "canon-pick",
    "The canon essays (at most three) a reviewer of this change should load, most at stake first.",
    gather_change,
)
async def canon_pick(jev, gathered: dict) -> dict:
    answer = await jev.ask("canon-pick", {"change": gathered["change"]}, {"essay": essay_question(gathered["essays"])})
    ranked = [
        (stem, round(value, 3)) for stem, value in top(answer["essay"]["probabilities"], len(gathered["essays"]) + 1)
    ]
    picks = [
        {"essay": f"{stem}.md", "title": gathered["essays"][stem]["title"], "probability": probability}
        for stem, probability in ranked
        if stem != NO_ESSAY and probability >= CANON_PICK
    ][:MAX_PICKS]
    return {"essays": picks, "probabilities": dict(ranked)}


def numbered_lines(repo: Path, query: dict) -> list[tuple[int, str]]:
    require(query, "claim", "file")
    path = repo / query["file"]
    if not path.is_file():
        raise BadInput(f"no such file: {query['file']}")
    lines = path.read_text(errors="replace").splitlines()
    start = query.get("start", 1)
    end = query.get("end", len(lines))
    selected = [(number, lines[number - 1]) for number in range(max(start, 1), min(end, len(lines)) + 1)]
    if not selected:
        raise BadInput(f"{query['file']} has no lines in {start}..{end}")
    if len(selected) > CHOICE_LIMIT * CHOICE_LIMIT or sum(len(text) for _, text in selected) > DOCUMENT_CHARS:
        raise BadInput(f"{query['file']} is too long to search; pass `start` and `end`")
    return selected


def gather_queries(payload: dict) -> dict:
    queries = payload.get("queries") or ([payload] if "claim" in payload else [])
    if not queries:
        raise BadInput("input needs `claim` and `file`, or `queries`")
    repo = Path(payload.get("repo", "."))
    gathered = []
    for query in queries:
        lines = numbered_lines(repo, query)
        gathered.append({"claim": query["claim"], "file": query["file"], "lines": lines})
    return {"queries": gathered}


def document(lines: list[tuple[int, str]]) -> str:
    return "\n".join(f"L{number}| {text}" for number, text in lines)


def windows(lines: list[tuple[int, str]]) -> dict[str, list[tuple[int, str]]]:
    chunks = [lines[index : index + CHOICE_LIMIT] for index in range(0, len(lines), CHOICE_LIMIT)]
    return {f"L{chunk[0][0]}-L{chunk[-1][0]}": chunk for chunk in chunks}


def where_question(options: list[str], unit: str) -> Choice:
    return Choice(
        instructions=(
            f"Each line of `document` starts with its id. Which {unit} holds the line that `claim` is about: the "
            "line a reviewer would cite for it, where the thing it names is stated or done?"
        ),
        criteria=dict.fromkeys(options),
    )


EXISTS = Noul(
    instructions="Does any line of `document` state, implement, or directly address what `claim` is about?",
    criteria=NoulCriteria(
        true="At least one line states, implements, or directly addresses it",
        false="No line of the document addresses it",
    ),
)


async def find(jev, query: dict) -> dict:
    lines = query["lines"]
    base_state = {"claim": query["claim"], "file": query["file"]}
    exists = None
    if len(lines) > CHOICE_LIMIT:
        chunks = windows(lines)
        answers = await jev.ask(
            "locate/window",
            {**base_state, "document": document(lines)},
            {"window": where_question(list(chunks), "range of line ids"), "exists": EXISTS},
        )
        lines = chunks[top(answers["window"]["probabilities"], 1)[0][0]]
        exists = answers["exists"]["noul"]
    questions = {"line": where_question([f"L{number}" for number, _ in lines], "line id")}
    if exists is None:
        questions["exists"] = EXISTS
    answers = await jev.ask("locate", {**base_state, "document": document(lines)}, questions)
    exists = answers["exists"]["noul"] if exists is None else exists
    ranked = top(answers["line"]["probabilities"])
    texts = dict(lines)
    best, probability = ranked[0]
    return {
        "claim": query["claim"],
        "file": query["file"],
        "line": int(best[1:]),
        "text": texts[int(best[1:])],
        "probability": round(probability, 3),
        "exists": round(exists, 3),
        "found": exists >= FOUND,
        "alternatives": [{"line": int(name[1:]), "probability": round(value, 3)} for name, value in ranked[1:]],
    }


@tool(
    "locate",
    "The line of a file that a claim or question is about, and whether the file addresses it at all.",
    gather_queries,
)
async def locate(jev, gathered: dict) -> dict:
    return {"locations": list(await asyncio.gather(*(find(jev, query) for query in gathered["queries"])))}
