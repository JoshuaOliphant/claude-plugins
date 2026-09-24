# ABOUTME: Jev tools for specs and decisions: spec-class, question-value, ac-quality, adr-worthy.
# ABOUTME: Code builds the questions and applies the spec skill's rules; Jev only grades what code hands it.
import asyncio

from typesafe_sdk import Choice, Noul, Score

from jevtools.core import top
from jevtools.registry import BadInput, tool

CLASSES = {
    "spike": (
        "A feasibility question: 'can we...', 'is it possible...', 'find out whether...'. What comes out is an "
        "answer, not code anyone keeps, even when acting on that answer later would be a large change."
    ),
    "bounded": (
        "A well-scoped change to a flow that `survey` shows already exists in this repo: a flag, an option, a "
        "small endpoint, a fix inside one module. If the survey found no existing flow to change, it is not bounded."
    ),
    "architectural": (
        "A project or a new subsystem, a change to how components fit together or to interfaces others depend on, "
        "or a feature with no existing flow in the repo to build on."
    ),
}
WEIGHT = list(CLASSES)
CLASS_CONFIDENCE = 0.7

VALUE_LEVELS = [
    (
        "The answer changes nothing that gets built: wording, naming, a preference nobody would notice, or a choice "
        "the code, the docs, or the request already make."
    ),
    "The answer changes a detail inside one behavior: a message, a default value, a limit, a format.",
    (
        "The answer changes which behaviors get built: it adds, removes, or reshapes an acceptance criterion or a "
        "flow a user sees."
    ),
    (
        "The answer changes the architecture or the scope: which components exist, how they fit together, an "
        "interface others depend on, or whether a whole part of the request is in or out."
    ),
]
ASK_VALUE = 1.7
ROUND_SIZE = 5

AC_DIMENSIONS = {
    "observable_then": Score(
        instructions=(
            "`criterion` is an acceptance criterion in Given/When/Then form. How well can a test assert its Then "
            "from outside the code?"
        ),
        criteria=[
            (
                "The Then names no outcome a test could check: a quality or intention ('handles the error gracefully', "
                "'works correctly', 'is fast'), or it is missing."
            ),
            (
                "The Then names an outcome but leaves what to check open, so two testers would assert different "
                "things ('shows an error', 'the data is updated'), or it can be checked only by reaching into internals."
            ),
            (
                "The Then states an outcome a test can assert exactly from outside: a message, a status, a value, a "
                "record present or absent, a count."
            ),
        ],
    ),
    "specific_given": Score(
        instructions=(
            "`criterion` is an acceptance criterion in Given/When/Then form. How concrete is its Given, the state "
            "the scenario starts from?"
        ),
        criteria=[
            "There is no Given, or it says nothing about the starting state ('Given the system', 'Given a user').",
            "The Given names the actor or the area but leaves out the state the outcome depends on.",
            "The Given is a concrete precondition: the specific state, data, or role the scenario starts from.",
        ],
    ),
    "single_behavior": Score(
        instructions=(
            "`criterion` is an acceptance criterion in Given/When/Then form. Does it describe one behavior? "
            "Several 'and' clauses in the Then are fine when they are all outcomes of the same action."
        ),
        criteria=[
            (
                "Several behaviors: the When holds two actions ('edits and saves', 'does X or Y'), or the Thens belong "
                "to different actions or features."
            ),
            "One action, but part of the Then strays into a separate concern that deserves its own criterion.",
            "One action and the outcomes of that one action.",
        ],
    ),
}
REWRITE_BELOW = 0.63

ADR_TESTS = {
    "hard_to_reverse": Noul(
        instructions=(
            "`ruling` is a decision made while building software. Would changing this decision later cost "
            "something real: a migration, rework across many places, lost data, or breaking the people or code "
            "that depend on it? Answer no when it can be undone by editing a line, a setting, or one small module."
        )
    ),
    "surprising": Noul(
        instructions=(
            "`ruling` is a decision made while building software. Would a capable engineer who later reads the "
            "code or the repo, without this record, wonder why it was done this way or be tempted to 'fix' it, "
            "because it departs from the obvious path or rests on a constraint the code does not show?"
        )
    ),
    "trade_off": Noul(
        instructions=(
            "`ruling` is a decision made while building software. Were there genuine alternatives, each viable, "
            "with this one picked over them for specific reasons? Answer no when it was the only sensible option "
            "or the alternatives were not seriously on the table."
        )
    ),
}
ADR_THRESHOLDS = {"hard_to_reverse": 0.65, "surprising": 0.5, "trade_off": 0.6}


def items_of(payload: dict, single: str, plural: str) -> list:
    items = payload.get(plural) or ([payload[single]] if single in payload else [])
    if not items or not isinstance(items, list):
        raise BadInput(f"input needs `{single}` or a non-empty `{plural}` list")
    return items


def text_of(item, field: str, where: str) -> str:
    value = item.get(field) if isinstance(item, dict) else item
    if not isinstance(value, str) or not value.strip():
        raise BadInput(f"{where} needs a non-empty `{field}`")
    return value


def gather_requests(payload: dict) -> dict:
    requests = []
    for item in items_of(payload, "request", "requests"):
        entry = item if isinstance(item, dict) else {**payload, "request": item}
        text_of(entry, "request", "each request")
        requests.append({"request": entry["request"], "survey": entry.get("survey", "")})
    return {"requests": requests}


def classify_question() -> Choice:
    return Choice(
        instructions=(
            "`request` is what a user asked a developer to spec out; `survey` is what a read of the code found: "
            "the files or modules it touches and whether a flow it changes already exists. Which class of work "
            "is it?"
        ),
        criteria=CLASSES,
    )


async def classify(jev, request: dict) -> dict:
    answers = await jev.ask("spec-class", request, {"class": classify_question()})
    probabilities = answers["class"]["probabilities"]
    ranked = top(probabilities, 2)
    pick, confidence = ranked[0]
    chosen = pick
    if confidence < CLASS_CONFIDENCE:
        chosen = max((name for name, _ in ranked), key=WEIGHT.index)
    return {
        "request": request["request"],
        "class": chosen,
        "jev_pick": pick,
        "confidence": round(confidence, 3),
        "heavier_if_unsure": chosen != pick,
        "probabilities": {name: round(p, 3) for name, p in probabilities.items()},
    }


@tool(
    "spec-class",
    "Classify a request as spike, bounded, or architectural; low confidence takes the heavier class.",
    gather_requests,
)
async def spec_class(jev, gathered: dict) -> dict:
    classes = await asyncio.gather(*(classify(jev, request) for request in gathered["requests"]))
    return {"classifications": list(classes)}


def gather_questions(payload: dict) -> dict:
    request = text_of(payload, "request", "input")
    questions = []
    for number, item in enumerate(items_of(payload, "question", "questions"), start=1):
        entry = item if isinstance(item, dict) else {"question": item}
        questions.append(
            {
                "id": str(entry.get("id", f"Q{number}")),
                "question": text_of(entry, "question", "each question"),
                "options": list(entry.get("options", [])),
                "frontier": bool(entry.get("frontier", True)),
            }
        )
    return {"request": request, "questions": questions, "round_size": int(payload.get("round_size", ROUND_SIZE))}


def value_question(index: int) -> Score:
    return Score(
        instructions=(
            f"`request` is what a user asked for. `questions[{index}]` is one question a developer might ask the "
            "user before building it, with the options the answer could take. How much would the user's answer "
            "change what gets built?"
        ),
        criteria=VALUE_LEVELS,
    )


@tool(
    "question-value",
    "Score how much each interview question's answer changes what gets built, and pick the round to ask.",
    gather_questions,
)
async def question_value(jev, gathered: dict) -> dict:
    questions = gathered["questions"]
    state = {
        "request": gathered["request"],
        "questions": [{"question": q["question"], "options": q["options"]} for q in questions],
    }
    answers = await jev.ask("question-value", state, {f"q{i}": value_question(i) for i in range(len(questions))})
    scored = [
        {
            "id": q["id"],
            "question": q["question"],
            "value": round(answers[f"q{i}"]["score"], 3),
            "probabilities": answers[f"q{i}"]["probabilities"],
            "frontier": q["frontier"],
        }
        for i, q in enumerate(questions)
    ]
    ranked = sorted(scored, key=lambda q: (not q["frontier"], -q["value"]))
    asked = 0
    for question in ranked:
        if not question["frontier"]:
            question["decision"] = "later"
        elif question["value"] < ASK_VALUE:
            question["decision"] = "assume"
        elif asked < gathered["round_size"]:
            question["decision"] = "ask"
            asked += 1
        else:
            question["decision"] = "next-round"
    return {"round": [q["id"] for q in ranked if q["decision"] == "ask"], "questions": ranked}


def gather_criteria(payload: dict) -> dict:
    criteria = []
    for number, item in enumerate(items_of(payload, "criterion", "criteria"), start=1):
        entry = item if isinstance(item, dict) else {"text": item}
        criteria.append({"id": str(entry.get("id", f"AC-{number}")), "text": text_of(entry, "text", "each criterion")})
    return {"criteria": criteria}


async def grade(jev, criterion: dict) -> dict:
    answers = await jev.ask("ac-quality", {"criterion": criterion["text"]}, AC_DIMENSIONS)
    scores = {
        name: round(answers[name]["score"] / (len(question.criteria) - 1), 3)
        for name, question in AC_DIMENSIONS.items()
    }
    weakest = min(scores, key=scores.get)
    return {
        "id": criterion["id"],
        **scores,
        "combined": scores[weakest],
        "weakest": weakest,
        "rewrite": scores[weakest] < REWRITE_BELOW,
    }


@tool(
    "ac-quality",
    "Grade each acceptance criterion: observable Then, specific Given, single behavior; flag the weak to rewrite.",
    gather_criteria,
)
async def ac_quality(jev, gathered: dict) -> dict:
    graded = await asyncio.gather(*(grade(jev, criterion) for criterion in gathered["criteria"]))
    return {"criteria": list(graded)}


def gather_rulings(payload: dict) -> dict:
    rulings = []
    for item in items_of(payload, "ruling", "rulings"):
        entry = item if isinstance(item, dict) else {"what": item}
        text_of(entry, "what", "each ruling")
        rulings.append(entry)
    return {"rulings": rulings}


async def weigh(jev, ruling: dict) -> dict:
    answers = await jev.ask("adr-worthy", {"ruling": ruling}, ADR_TESTS)
    tests = {name: round(answers[name]["noul"], 3) for name in ADR_TESTS}
    return {"what": ruling["what"], **tests, "offer_adr": all(tests[name] >= ADR_THRESHOLDS[name] for name in tests)}


@tool(
    "adr-worthy",
    "Whether a ruling deserves an ADR: hard to reverse, surprising, and a real trade-off, all three.",
    gather_rulings,
)
async def adr_worthy(jev, gathered: dict) -> dict:
    weighed = await asyncio.gather(*(weigh(jev, ruling) for ruling in gathered["rulings"]))
    return {"rulings": list(weighed)}
