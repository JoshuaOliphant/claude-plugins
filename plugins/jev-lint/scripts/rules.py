# ABOUTME: The semantic lint rules: one Jev question per rule, tied to a unit kind, plus how an answer becomes a finding.
# ABOUTME: Each rule also names the ruff rules that already catch the same problem syntactically, so they can move to ruff.

from collections.abc import Callable
from dataclasses import dataclass, field

from extract import Unit, is_test_path
from typesafe_sdk import Choice, Noul, NoulCriteria


def no_static_equivalent(label: str, unit: Unit) -> tuple[str, ...]:
    return ()


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str
    message: str
    question: Noul | Choice
    acceptable: frozenset[str] = frozenset()
    threshold: float = 0.5
    actions: dict[str, str] = field(default_factory=dict, hash=False)
    applies: Callable[[Unit], bool] = lambda unit: True
    static_equivalents: Callable[[str, Unit], tuple[str, ...]] = no_static_equivalent

    def probability(self, answer) -> tuple[float, str]:
        if isinstance(self.question, Noul):
            return answer.noul, "yes"
        flagged = {
            label: p for label, p in answer.probabilities.items() if label not in self.acceptable
        }
        return sum(flagged.values()), max(flagged, key=flagged.get)

    def message_for(self, label: str) -> str:
        return self.actions.get(label, self.message)


def comment_static_equivalents(label: str, unit: Unit) -> tuple[str, ...]:
    return ("ERA001",) if label == "commented_out_code" else ()


COMMENT_KIND = Rule(
    id="comment-kind",
    kind="comment",
    message="comment does not earn its place: only a why the code cannot show survives",
    acceptable=frozenset({"why", "todo"}),
    actions={
        "narrates": "delete: the comment restates the code",
        "section_banner": "delete: organize with functions or modules instead of banners",
        "commented_out_code": "delete: version control keeps the old code",
        "change_history": "move to the commit message: it describes how the code changed",
        "misleading": "fix or delete: the comment disagrees with the code",
        "belongs_in_docs": "move to documentation: it explains usage or design, not these lines",
    },
    static_equivalents=comment_static_equivalents,
    question=Choice(
        instructions=(
            "Classify the Python comment `comment`, reading it against the code around it "
            "(`code_before`, `code_after`, and `inline_code` when the comment trails a line). "
            "Pick the single best description."
        ),
        criteria={
            "why": (
                "Explains something the code cannot show about these lines: an external "
                "constraint (a library, protocol, platform, or API contract), a legal or license "
                "header, a justified lint or type-checker suppression, an issue link, or the "
                "reason behind a non-obvious choice that a reader would otherwise undo."
            ),
            "todo": "A TODO or FIXME note recording known unfinished work.",
            "narrates": (
                "Restates what the nearby code does or is about to do, including short labels "
                "for the next line such as 'Limit to 20 results', 'Sort tags', or 'Fallback to "
                "default if invalid'."
            ),
            "section_banner": (
                "A divider, heading, or step label that organizes the file, such as "
                "'--- helpers ---' or 'Step 2: parse'."
            ),
            "commented_out_code": "Code disabled by commenting it out.",
            "change_history": (
                "Describes how the code changed or used to be: 'now uses', 'previously', "
                "'refactored', 'new version', 'superseded by', 'instead of the old'."
            ),
            "misleading": "Contradicts or no longer matches the code next to it.",
            "belongs_in_docs": (
                "Explains how to use the module, how the system fits together, or the design "
                "rationale for a whole feature: material for a README, guide, or architecture "
                "note rather than for the next few lines."
            ),
        },
    ),
)


def handler_static_equivalents(label: str, unit: Unit) -> tuple[str, ...]:
    rules = []
    if unit.facts.get("bare"):
        rules.append("E722")
    if unit.facts.get("broad"):
        rules.append("BLE001")
    only = unit.facts.get("only_statement")
    if only == "Pass":
        rules.append("S110")
    elif only == "Continue":
        rules.append("S112")
    return tuple(rules)


SILENT_FAILURE = Rule(
    id="silent-failure",
    kind="handler",
    message="except clause hides the failure from callers",
    static_equivalents=handler_static_equivalents,
    question=Noul(
        instructions=(
            "Does the except clause `handler` of `try_statement` hide a failure that matters, so "
            "callers carry on as if nothing went wrong?"
        ),
        criteria=NoulCriteria(
            true=(
                "It swallows the exception with pass, continue, a default or fallback value, or "
                "a log below error level, the operation it guarded mattered to the caller, and "
                "nothing is re-raised or reported."
            ),
            false=(
                "It re-raises, raises a different error, returns an explicit failure the caller "
                "must handle, or reports it as an error. Also no when the exception is an "
                "expected outcome handled on purpose: a missing optional file, a probe whose "
                "documented answer is 'not found', or best-effort cleanup such as killing a "
                "process that may already be gone or deleting a temporary file."
            ),
        ),
    ),
)

IO_MIXED_WITH_LOGIC = Rule(
    id="io-mixed-with-logic",
    threshold=0.7,
    kind="function",
    message="function mixes I/O with domain logic; keep I/O at the edges",
    question=Noul(
        instructions=(
            "Does `function` both perform I/O and hold domain logic that deserves its own "
            "unit tests?"
        ),
        criteria=NoulCriteria(
            true=(
                "It reads or writes files, calls the network, a database, or a subprocess, reads "
                "environment variables, or prints, AND it computes, validates, or makes business "
                "decisions in the same body."
            ),
            false=(
                "It is pure logic, pure I/O, or a thin entry point that wires I/O to other "
                "functions that hold the decisions."
            ),
        ),
    ),
)

NAME_HIDES_SIDE_EFFECTS = Rule(
    id="name-hides-side-effects",
    threshold=0.7,
    kind="function",
    message="function does something significant its name does not suggest",
    question=Noul(
        instructions=(
            "Does `function` do something significant that its name `qualified_name` does not "
            "lead a reader to expect?"
        ),
        criteria=NoulCriteria(
            true=(
                "The name promises a read, a calculation, a check, or a formatted value (get_, "
                "find_, load_, is_, has_, check_, validate_, parse_, format_, build_, compute_, a "
                "plain noun), yet the function writes files, mutates its arguments or global "
                "state, makes network calls, deletes data, or exits the process."
            ),
            false=(
                "The name already announces effects: main, run_, cmd_, handle_, do_, apply_, "
                "save_, write_, update_, delete_, send_, sync_, install_, setup_, a verb for the "
                "effect itself, or a test_ function. Or the function has no significant effects."
            ),
        ),
    ),
)

DOCSTRING_QUALITY = Rule(
    id="docstring-quality",
    threshold=0.7,
    kind="function",
    message="docstring is inaccurate, empty of information, or hides a surprise",
    acceptable=frozenset({"accurate"}),
    actions={
        "restates_name": "delete or rewrite: the docstring only repeats the name",
        "contradicts": "fix: the docstring claims behavior the code does not have",
        "omits_surprise": "extend: name the side effect or failure mode a caller must know",
    },
    applies=lambda unit: "docstring" in unit.state,
    question=Choice(
        instructions="Judge the docstring `docstring` against the code in `function`.",
        criteria={
            "accurate": (
                "Describes the behavior correctly and tells a caller something the name and "
                "signature do not."
            ),
            "restates_name": "Only repeats what the name and signature already say.",
            "contradicts": "Claims behavior the code does not have, or no longer has.",
            "omits_surprise": (
                "Correct as far as it goes, but leaves out a side effect or failure mode a "
                "caller needs to know."
            ),
        },
    ),
)

LOG_EXPOSURE = Rule(
    id="log-exposure",
    kind="log_call",
    message="log call may expose sensitive data",
    acceptable=frozenset({"harmless"}),
    question=Choice(
        instructions=(
            "What kind of data does the log call `log_call` write out? Use "
            "`enclosing_function` to understand what its variables hold."
        ),
        criteria={
            "harmless": "Operational detail with no sensitive values.",
            "secret": "A credential, token, password, API key, or private key.",
            "personal_data": "Data that identifies a person: email, name, address, phone, or IP.",
            "financial": "Card numbers, bank accounts, or money amounts tied to a person.",
        },
    ),
)

TEST_SMELL = Rule(
    id="test-smell",
    threshold=0.7,
    kind="function",
    message="test cannot catch the regression it claims to guard",
    acceptable=frozenset({"meaningful", "smoke"}),
    applies=lambda unit: unit.name.rsplit(".", 1)[-1].startswith("test_"),
    question=Choice(
        instructions=(
            "Judge whether the test `function` can fail when the behavior it names breaks."
        ),
        criteria={
            "meaningful": "Drives real code and asserts outcomes that would change if it broke.",
            "smoke": (
                "Has no assertion but drives real code whose failure raises, and its name "
                "claims only that the code runs or does not crash."
            ),
            "tautology": "Its assertions compare values the test itself set up and cannot fail.",
            "mocks_unit_under_test": (
                "Replaces the very code it claims to test with a mock, then asserts on the mock."
            ),
            "overclaims": "Its name or docstring promises more than its assertions check.",
            "no_real_assertion": (
                "Its only checks are that a value exists or is truthy, when the name promises a "
                "specific result."
            ),
        },
    ),
)

SYMPTOM_WORKAROUND = Rule(
    id="symptom-workaround",
    kind="hunk",
    message="change hides a symptom instead of fixing its cause",
    question=Noul(
        instructions=(
            "Does the change in `hunk` (removed lines in `removed`, added lines in `added`) hide "
            "a symptom instead of fixing its cause?"
        ),
        criteria=NoulCriteria(
            true=(
                "It adds a retry, sleep, broad except, default fallback, skip or xfail, a "
                "loosened check, or a special case that makes a failure go away without "
                "explaining or removing why it happens."
            ),
            false="It changes behavior at the cause, or is unrelated to handling a failure.",
        ),
    ),
)

TEST_WEAKENING = Rule(
    id="test-weakening",
    kind="hunk",
    message="change weakens the tests",
    applies=lambda unit: is_test_path(unit.path),
    question=Noul(
        instructions=(
            "Does the change in `hunk` (removed lines in `removed`, added lines in `added`) "
            "weaken the tests?"
        ),
        criteria=NoulCriteria(
            true=(
                "It removes or loosens assertions, widens expected values, adds skip or xfail, or "
                "deletes test cases, without adding equivalent checks."
            ),
            false="The tests check at least as much after the change as before.",
        ),
    ),
)

RULES = [
    COMMENT_KIND,
    SILENT_FAILURE,
    IO_MIXED_WITH_LOGIC,
    NAME_HIDES_SIDE_EFFECTS,
    DOCSTRING_QUALITY,
    LOG_EXPOSURE,
    TEST_SMELL,
    SYMPTOM_WORKAROUND,
    TEST_WEAKENING,
]
