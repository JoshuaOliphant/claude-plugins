# ABOUTME: Jev tools about compost itself and its runs: classify-change, route, rulings-lint, stop-guard.
# ABOUTME: Code gathers diffs, descriptions, passages, and final messages; Jev picks or checks; thresholds decide.
import asyncio
import re
from pathlib import Path

import pile
from typesafe_sdk import Choice, Noul

from jevtools.core import top
from jevtools.registry import BadInput, require, tool

PLUGIN_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_STOPS = [
    "merging to the repository's default branch",
    (
        "irreversible or outward-facing actions: force-push, history rewrites on shared branches, deploys, data "
        "deletion, messages that reach people"
    ),
    "approval of an architectural spec",
    "starting a Claude Code workflow the agent wrote itself, since one can spawn dozens of agents",
]
RULINGS = [
    (
        "Decide, record the ruling (what, why, cost if wrong) as an issue comment, and proceed. Stop for the user "
        "only for: " + "; ".join(ALLOWED_STOPS) + "."
    ),
    (
        "Never ask permission to spawn subagents or agent teams; only a self-written Claude Code workflow needs the "
        "user's ask. Review is always done by subagents."
    ),
    (
        "No test-first ritual: writing the test or the code first is the agent's call, but every new or changed "
        "test must be seen failing for the right reason."
    ),
    "Fit tests into the existing suite: extend, parametrize, or update existing tests; a duplicate test is a defect.",
    "Track work in the repo's issue tracker: never beads, TodoWrite, or markdown plan or ledger files.",
    "Never size work by time or context-window budget; the model judges what fits.",
    "Never tell the agent to redact secrets or personal data; a hook does it.",
    "No ALL-CAPS rules, Iron Laws, HARD-GATE tags, or threats: state the rule and its reason.",
    "Refactors replace, never deprecate: no compatibility shims.",
    "100% line coverage is a negotiable gate: propose an exclusion rather than tests that prove nothing.",
]


def skill_descriptions(root: Path = PLUGIN_ROOT) -> dict[str, str]:
    descriptions = {}
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        if match := re.search(r"^description: (.*)$", path.read_text(), re.MULTILINE):
            descriptions[path.parent.name] = match.group(1).strip()
    return descriptions


def skill_texts(skills: list[str], root: Path = PLUGIN_ROOT) -> dict[str, str]:
    paths = {skill: root / "skills" / skill / "SKILL.md" for skill in skills}
    if "canon" in paths:
        paths["canon"] = root / "canon" / "README.md"
    return {skill: path.read_text() for skill, path in paths.items() if path.exists()}


VERDICTS = {
    "adopt": (
        "Better than what `compost_skills` says and fits compost as written: a sharper step, a fixed bug, a "
        "clearer example, or a check compost lacks, with nothing in it that `rulings` forbid."
    ),
    "adapt": (
        "A good idea compost lacks, in a form that conflicts with `rulings`: it arrives inside an approval gate, "
        "a test-first ritual, beads or ledger files, or a size rule. Take the idea, not the text."
    ),
    "ignore": (
        "Nothing for compost to take: rewording or trimming, churn, tooling, model names, or setup specific to the "
        "source, or an idea `compost_skills` already covers."
    ),
}
VERDICT = Choice(
    instructions=(
        "`change.diff` is an upstream change to `change.path` in `source`, a skill collection compost was built "
        "from. `compost_skills` holds the compost skills that file fed (empty when it fed none; `compost_catalog` "
        "lists every compost skill), and `rulings` are compost's settled rules. compost was rewritten from these "
        "sources, so much of what an upstream change adds is already in `compost_skills` in different words; that "
        "is ignore. Only what compost does not already say can be adopt or adapt. What should compost do with "
        "this change?"
    ),
    criteria=VERDICTS,
)
DIFF_CHARS = 12000
RECORD_IGNORE_AT = 0.6


def fed_skills(path: str, feeds: dict[str, list[str]]) -> list[str]:
    by_skill, _ = pile.map_changes([path], feeds)
    return sorted(by_skill)


def describe_changes(source: str, changes: list[dict], root: Path = PLUGIN_ROOT) -> dict:
    fed = sorted({skill for change in changes for skill in change["skills"]})
    return {
        "source": source,
        "changes": [change | {"diff": change["diff"][:DIFF_CHARS]} for change in changes],
        "skills": skill_texts(fed, root),
        "catalog": skill_descriptions(root),
    }


def gather_changes(payload: dict) -> dict:
    require(payload, "source", "paths")
    if not payload["paths"]:
        raise BadInput("`paths` is empty")
    try:
        sources = {source.name: source for source in pile.load(Path(payload.get("pile", pile.PILE)))}
        if payload["source"] not in sources:
            raise BadInput(f"no source named {payload['source']!r} in pile.toml")
        source = sources[payload["source"]]
        clone = pile.clone_path(source.repo)
        if not (clone / ".git").exists():
            pile.sync_clone(source.repo)
        pin = payload.get("pin", source.pin)
        head = payload.get("head") or pile.git("-C", str(clone), "rev-parse", "origin/HEAD").strip()
        diffs = {path: pile.git("-C", str(clone), "diff", pin, head, "--", path) for path in payload["paths"]}
    except pile.PileError as error:
        raise BadInput(str(error)) from error
    changes = [{"path": path, "skills": fed_skills(path, source.feeds), "diff": diff} for path, diff in diffs.items()]
    return describe_changes(source.name, changes)


async def classify(jev, gathered: dict, change: dict) -> dict:
    decided = {"path": change["path"], "skills": change["skills"]}
    if not change["diff"].strip():
        return decided | {"verdict": "ignore", "confidence": 1.0, "probabilities": {}, "needs_reading": False}
    state = {
        "source": gathered["source"],
        "change": {"path": change["path"], "diff": change["diff"]},
        "compost_skills": {
            skill: gathered["skills"][skill] for skill in change["skills"] if skill in gathered["skills"]
        },
        "compost_catalog": gathered["catalog"],
        "rulings": RULINGS,
    }
    answers = await jev.ask("classify-change", state, {"verdict": VERDICT})
    probabilities = answers["verdict"]["probabilities"]
    verdict, confidence = top(probabilities, 1)[0]
    return decided | {
        "verdict": verdict,
        "confidence": round(confidence, 3),
        "probabilities": {name: round(value, 3) for name, value in probabilities.items()},
        "needs_reading": verdict != "ignore" or confidence < RECORD_IGNORE_AT,
    }


@tool(
    "classify-change",
    "Sort upstream changes into adopt, adapt, or ignore; confident ignores need no reading.",
    gather_changes,
)
async def classify_change(jev, gathered: dict) -> dict:
    changes = await asyncio.gather(*(classify(jev, gathered, change) for change in gathered["changes"]))
    return {
        "source": gathered["source"],
        "changes": list(changes),
        "to_read": [change["path"] for change in changes if change["needs_reading"]],
    }


NO_SKILL = "none"
CLOSE_MARGIN = 0.15


def gather_route(payload: dict) -> dict:
    prompts = payload.get("prompts") or ([payload["prompt"]] if "prompt" in payload else [])
    if not prompts:
        raise BadInput("input needs `prompt` or `prompts`")
    skills = skill_descriptions(Path(payload.get("plugin", PLUGIN_ROOT)))
    if not skills:
        raise BadInput("no skills with a description found")
    return {"prompts": prompts, "skills": skills}


def route_question(skills: dict[str, str]) -> Choice:
    return Choice(
        instructions=(
            "An agent is choosing which skill to load for the request in `request`. "
            "Which skill's description fits the request best?"
        ),
        criteria={**skills, NO_SKILL: "None of these skills fits the request."},
    )


async def route_one(jev, prompt: str, question: Choice) -> dict:
    answers = await jev.ask("route", {"request": prompt}, {"skill": question})
    probabilities = answers["skill"]["probabilities"]
    (skill, first), (_, second) = top(probabilities, 2)
    margin = first - second
    return {
        "prompt": prompt,
        "skill": skill,
        "margin": round(margin, 3),
        "close": margin < CLOSE_MARGIN,
        "probabilities": {name: round(value, 3) for name, value in top(probabilities, len(probabilities))},
    }


@tool(
    "route", "Which compost skill each prompt should load, or none; the regression eval for descriptions.", gather_route
)
async def route(jev, gathered: dict) -> dict:
    question = route_question(gathered["skills"])
    routes = await asyncio.gather(*(route_one(jev, prompt, question) for prompt in gathered["prompts"]))
    return {"routes": list(routes)}


LINTED = ("skills", "canon", "agents")
MIN_PASSAGE = 40
EXCERPT = 240
USER_IN_THE_LOOP = {
    "skills/spec/": (
        "spec interviews the user: asking them questions is the job, and an architectural spec waits for approval"
    ),
    "skills/setup/": "setup runs once per repo with the user present, and changes to their own files are offers",
    "skills/finish/": "finish integrates work: merging to the default branch and discarding work are the user's call",
    "skills/slice/references/map-issue.md": "a map's destination is settled with the user in an interview round",
}
POLICY = {
    "allowed_stops": ALLOWED_STOPS,
    "context": (
        "Each passage comes from an instruction file for an autonomous coding agent that often runs unattended "
        "while the user is away. `passage.user_in_the_loop`, when set, says why the user takes part in this part "
        "of the workflow."
    ),
}
GATE = Noul(
    instructions=(
        "Does `passage.text` make the agent's progress wait on the user's approval, consent, choice, or answer: "
        "a gate the agent may not pass on its own judgment, even when the user is away?"
    )
)
GATE_ALLOWED = Noul(
    instructions=(
        "Is that gate one of `policy.allowed_stops`, or part of the work `passage.user_in_the_loop` describes? "
        "Approving a plan, a design for bounded work, a worktree, a commit, or the use of subagents is none of "
        "these."
    )
)
RULES = {
    "asks_to_spawn": (
        "Does `passage.text` tell the agent to ask the user for permission before spawning subagents or "
        "teammates? Asking before starting a Claude Code workflow the agent wrote itself is compost's own rule."
    ),
    "tdd_ritual": (
        "Does `passage.text` prescribe a test-first ritual: red-green-refactor cycles, writing one test at a time "
        "before any code, or throwing away code written before its test and starting over? Watching each new test "
        "fail for the right reason is compost's own rule, even when that means undoing a change for the red run "
        "and putting it back; that is not a ritual."
    ),
    "size_rule": (
        "Does `passage.text` limit how much work the agent takes on by time or context-window budget (for "
        "example, 'tasks of 2-5 minutes' or 'sized to fit one session')? Scoping work to one issue or one "
        "behavior, or noting that work will outlast a session, is not a size rule."
    ),
    "redaction": "Does `passage.text` tell the agent to redact or strip secrets, credentials, or personal data?",
    "other_tracker": (
        "Does `passage.text`, anywhere in it, tell the agent to track tasks or progress in beads (`bd`), TodoWrite "
        "or TaskCreate, or markdown plan or ledger files, instead of the issue tracker? compost's local tracker, "
        "markdown issue and decision files under `.scratch/`, is an issue tracker, not a ledger."
    ),
    "new_test_bias": (
        "Does `passage.text` tell the agent to write a new test file, or a separate new test per requirement, "
        "where an existing test could be extended, parametrized, or updated? Worked examples of a bad test, "
        "Gherkin `.feature` files that state the acceptance criteria, and advice on which existing test to extend "
        "are not."
    ),
}
LINT_QUESTIONS = {"gate": GATE, "allowed": GATE_ALLOWED} | {
    rule: Noul(instructions=text) for rule, text in RULES.items()
}
RULE_NAMES = ["unallowed_stop", *RULES]
FLAG_AT = {rule: 0.5 for rule in RULE_NAMES} | {"unallowed_stop": 0.45, "tdd_ritual": 0.7}


def user_in_the_loop(file: str) -> str | None:
    return next((reason for prefix, reason in USER_IN_THE_LOOP.items() if file.startswith(prefix)), None)


def passage(file: str, line: int, heading: str, text: str) -> dict:
    return {"file": file, "line": line, "heading": heading, "text": text, "user_in_the_loop": user_in_the_loop(file)}


def passages(path: Path, file: str) -> list[dict]:
    units, heading, block, start, fenced = [], "", [], 1, False
    for number, line in enumerate([*path.read_text().splitlines(), ""], start=1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        ends_block = not fenced and (not line.strip() or re.match(r"^(\d+\.|-) ", line))
        if ends_block and block:
            text = "\n".join(block).strip()
            if len(text) > MIN_PASSAGE:
                units.append(passage(file, start, heading, text))
            block = []
        if not fenced and line.startswith("#"):
            heading = line.lstrip("# ").strip()
        elif line.strip() or fenced:
            if not block:
                start = number
            block.append(line)
    return units


def linted_files(root: Path) -> list[str]:
    files = [path for part in LINTED for path in sorted((root / part).rglob("*.md"))]
    return [str(path.relative_to(root)) for path in files] + (["README.md"] if (root / "README.md").exists() else [])


def gather_passages(payload: dict) -> dict:
    root = Path(payload.get("plugin", PLUGIN_ROOT))
    files = payload.get("paths") or linted_files(root)
    if missing := [file for file in files if not (root / file).is_file()]:
        raise BadInput(f"no such file: {', '.join(missing)}")
    units = [unit for file in files for unit in passages(root / file, file)]
    if not units:
        raise BadInput("no passages to lint")
    return {"passages": units}


async def lint(jev, unit: dict) -> dict[str, float]:
    answers = await jev.ask("rulings-lint", {"policy": POLICY, "passage": unit}, LINT_QUESTIONS)
    scores = {rule: answers[rule]["noul"] for rule in RULES}
    gate, allowed = answers["gate"]["noul"], answers["allowed"]["noul"]
    return {"unallowed_stop": gate * (1 - allowed)} | scores | {"gate": gate, "allowed": allowed}


@tool("rulings-lint", "Passages of compost's own text that drift from its rulings, per rule.", gather_passages)
async def rulings_lint(jev, gathered: dict) -> dict:
    units = gathered["passages"]
    scores = await asyncio.gather(*(lint(jev, unit) for unit in units))
    flags = {}
    for rule in RULE_NAMES:
        hits = [(unit, score[rule]) for unit, score in zip(units, scores, strict=True) if score[rule] >= FLAG_AT[rule]]
        flags[rule] = [
            {
                "file": unit["file"],
                "line": unit["line"],
                "heading": unit["heading"],
                "excerpt": unit["text"][:EXCERPT],
                "probability": round(probability, 3),
            }
            for unit, probability in sorted(hits, key=lambda hit: -hit[1])
        ]
    return {"passages": len(units), "flagged": sum(map(len, flags.values())), "flags": flags}


MESSAGE_CHARS = 4000
BLOCK_AT = 0.5
RUN = (
    "The agent is running compost:implement, an unattended run that works a parent issue's sub-issues to done "
    "while the user is away. It decides open questions itself and records each ruling as an issue comment."
)
MESSAGE_WAITS = Noul(
    instructions=(
        "`message` is the last thing the agent said before ending its turn. Does it end by waiting on the user: a "
        "question for them to answer, a choice or approval for them to make, or input for them to give, before "
        "the work goes on? A report of finished work, or a statement of what the agent does next, is not waiting."
    )
)
MESSAGE_ALLOWED = Noul(
    instructions=(
        "Is what `message` waits on one of `allowed_stops`? Answer no when it waits on nothing, or on anything "
        "else: a design or library choice, a policy, which option or approach to take, permission to commit, "
        "push a feature branch, file an issue, or keep going."
    )
)


def gather_stop(payload: dict) -> dict:
    require(payload, "message")
    message = str(payload["message"]).strip()
    if not message:
        raise BadInput("`message` is empty")
    return {"message": message[-MESSAGE_CHARS:]}


@tool(
    "stop-guard", "Whether an implement run's final message stops for something outside the allowed stops.", gather_stop
)
async def stop_guard(jev, gathered: dict) -> dict:
    state = {"run": RUN, "allowed_stops": ALLOWED_STOPS, "message": gathered["message"]}
    answers = await jev.ask("stop-guard", state, {"waits": MESSAGE_WAITS, "allowed": MESSAGE_ALLOWED})
    waits, allowed = answers["waits"]["noul"], answers["allowed"]["noul"]
    score = waits * (1 - allowed)
    return {
        "block": score >= BLOCK_AT,
        "score": round(score, 3),
        "waits": round(waits, 3),
        "allowed": round(allowed, 3),
    }
