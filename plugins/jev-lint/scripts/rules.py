# ABOUTME: The semantic lint rules: one Jev question per rule, tied to a unit kind, plus how an answer becomes a finding.
# ABOUTME: Noul rules flag on the yes-probability; Choice rules flag on the probability mass outside their acceptable labels.

from collections.abc import Callable
from dataclasses import dataclass

from extract import Unit, is_test_path
from typesafe_sdk import Choice, Noul, NoulCriteria


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str
    message: str
    question: Noul | Choice
    acceptable: frozenset[str] = frozenset()
    applies: Callable[[Unit], bool] = lambda unit: True

    def probability(self, answer) -> tuple[float, str]:
        if isinstance(self.question, Noul):
            return answer.noul, "yes"
        flagged = {
            label: p for label, p in answer.probabilities.items() if label not in self.acceptable
        }
        return sum(flagged.values()), max(flagged, key=flagged.get)


COMMENT_KIND = Rule(
    id="comment-kind",
    kind="comment",
    message="comment does not earn its place: only a why the code cannot show survives",
    acceptable=frozenset({"why", "todo"}),
    question=Choice(
        instructions=(
            "Classify the Python comment `comment`, reading it against the code around it "
            "(`code_before`, `code_after`, and `inline_code` when the comment trails a line). "
            "Pick the single best description."
        ),
        criteria={
            "why": (
                "Explains something the code cannot show: an external constraint (a library, "
                "protocol, platform, or API contract), a legal or license header, a justified "
                "lint or type-checker suppression, an issue link, or the reason behind a "
                "non-obvious choice."
            ),
            "todo": "A TODO or FIXME note recording known unfinished work.",
            "narrates": "Restates what the nearby code does, in words the code already says.",
            "section_banner": (
                "A divider, heading, or step label that organizes the file, such as "
                "'--- helpers ---' or 'Step 2: parse'."
            ),
            "commented_out_code": "Code disabled by commenting it out.",
            "change_history": (
                "Describes how the code changed or used to be: 'now uses', 'previously', "
                "'refactored', 'new version', 'instead of the old'."
            ),
            "misleading": "Contradicts or no longer matches the code next to it.",
        },
    ),
)

SILENT_FAILURE = Rule(
    id="silent-failure",
    kind="handler",
    message="except clause hides the failure from callers",
    question=Noul(
        instructions=(
            "Does the except clause `handler` of `try_statement` hide the failure, so callers "
            "carry on as if nothing went wrong?"
        ),
        criteria=NoulCriteria(
            true=(
                "It swallows the exception: pass, continue, returns a default or fallback value, "
                "or only logs below error level, and nothing is re-raised or reported."
            ),
            false=(
                "It re-raises, raises a different error, returns an explicit failure the caller "
                "must handle, reports it as an error, or catches an exception that is an "
                "expected, fully handled outcome (such as a missing optional file)."
            ),
        ),
    ),
)

IO_MIXED_WITH_LOGIC = Rule(
    id="io-mixed-with-logic",
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

VENDOR_LEAK = Rule(
    id="vendor-leak",
    kind="function",
    message="third-party framework or vendor type leaks into domain logic",
    question=Noul(
        instructions=(
            "Does `function` hold domain logic while taking, returning, or depending on a "
            "third-party framework or vendor type that could stay at the edge?"
        ),
        criteria=NoulCriteria(
            true=(
                "Domain decisions are made directly on a vendor object, such as an HTTP response, "
                "ORM session, SDK client, or web-framework request, or such a type crosses into "
                "or out of the logic."
            ),
            false=(
                "It uses only the language, the standard library, and the project's own types, "
                "or it is an adapter whose job is to translate a vendor type at the edge."
            ),
        ),
    ),
)

NAME_HIDES_SIDE_EFFECTS = Rule(
    id="name-hides-side-effects",
    kind="function",
    message="function does something significant its name does not suggest",
    question=Noul(
        instructions=(
            "Does `function` do something significant that its name `qualified_name` does not "
            "suggest?"
        ),
        criteria=NoulCriteria(
            true=(
                "It writes files, mutates its arguments or global state, makes network calls, "
                "deletes data, or exits the process, and a reader of the name would not expect it."
            ),
            false="The name tells a reader everything important the function does.",
        ),
    ),
)

DOCSTRING_QUALITY = Rule(
    id="docstring-quality",
    kind="function",
    message="docstring is inaccurate, empty of information, or hides a surprise",
    acceptable=frozenset({"accurate"}),
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
    kind="function",
    message="test cannot catch the regression it claims to guard",
    acceptable=frozenset({"meaningful"}),
    applies=lambda unit: unit.name.rsplit(".", 1)[-1].startswith("test_"),
    question=Choice(
        instructions=(
            "Judge whether the test `function` can fail when the behavior it names breaks."
        ),
        criteria={
            "meaningful": "Drives real code and asserts outcomes that would change if it broke.",
            "tautology": "Its assertions compare values the test itself set up and cannot fail.",
            "mocks_unit_under_test": (
                "Replaces the very code it claims to test with a mock, then asserts on the mock."
            ),
            "overclaims": ("Its name or docstring promises more than its assertions check."),
            "no_real_assertion": "Asserts nothing, or only that something is not None or truthy.",
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
    VENDOR_LEAK,
    NAME_HIDES_SIDE_EFFECTS,
    DOCSTRING_QUALITY,
    LOG_EXPOSURE,
    TEST_SMELL,
    SYMPTOM_WORKAROUND,
    TEST_WEAKENING,
]
