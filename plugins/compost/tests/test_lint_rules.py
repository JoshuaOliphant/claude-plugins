# ABOUTME: Tests for rules.py: how answers become finding probabilities, rule validation, ruff mapping, and prompt contracts.
# ABOUTME: Answers are the plain answer dicts Jev.ask returns, built by conftest helpers.
import re

import pytest
from conftest import choice
from extract import STATE_KEYS, Unit
from rules import (
    COMMENT_KIND,
    DOCSTRING_QUALITY,
    RULES,
    SILENT_FAILURE,
    TEST_SMELL,
    TEST_WEAKENING,
    Rule,
)
from typesafe_sdk import Choice, Noul


def _unit(kind="function", name="f", path="pkg/m.py", **state):
    return Unit(kind, path, 1, name, state)


def _handler(**facts):
    return Unit("handler", "m.py", 1, "h", {}, facts)


def test_choice_rule_sums_mass_outside_acceptable_and_names_top_problem():
    probabilities = {"why": 0.4, "todo": 0.05, "narrates": 0.3, "section_banner": 0.2, "misleading": 0.05}
    answer = choice("why", probabilities=probabilities)
    probability, label = COMMENT_KIND.probability(answer)
    assert round(probability, 2) == 0.55
    assert label == "narrates"


def test_choice_answer_with_only_acceptable_labels_scores_zero():
    assert COMMENT_KIND.probability(choice("why", probabilities={"why": 0.9, "todo": 0.1})) == (0.0, "why")


def test_docstring_rule_applies_only_with_a_docstring():
    assert DOCSTRING_QUALITY.applies(_unit(docstring="Doc."))
    assert not DOCSTRING_QUALITY.applies(_unit())


def test_test_smell_applies_to_test_functions_including_methods():
    assert TEST_SMELL.applies(_unit(name="TestOrders.test_total"))
    assert not TEST_SMELL.applies(_unit(name="total"))
    assert not TEST_SMELL.applies(_unit(kind="log_call", name="test_total"))


def test_weakening_applies_to_test_path_hunks_only():
    assert TEST_WEAKENING.applies(_unit(kind="hunk", path="tests/test_orders.py"))
    assert not TEST_WEAKENING.applies(_unit(kind="hunk", path="pkg/orders.py"))
    assert not TEST_WEAKENING.applies(_unit(kind="function", path="tests/test_orders.py"))


def test_a_rule_flags_at_its_own_threshold_unless_overridden():
    assert SILENT_FAILURE.threshold == 0.7
    assert SILENT_FAILURE.flags(0.7)
    assert not SILENT_FAILURE.flags(0.69)
    assert SILENT_FAILURE.flags(0.0, override=0.0)
    assert not SILENT_FAILURE.flags(0.95, override=0.96)


def test_comment_labels_carry_their_own_action():
    assert COMMENT_KIND.message_for("belongs_in_docs").startswith("move to documentation")
    assert COMMENT_KIND.message_for("change_history").startswith("move to the commit message")
    assert SILENT_FAILURE.message_for("yes") == SILENT_FAILURE.message


def test_commented_out_code_maps_to_ruff_eradicate():
    unit = _unit(kind="comment")
    assert COMMENT_KIND.static_equivalents("commented_out_code", unit) == ("ERA001",)
    assert COMMENT_KIND.static_equivalents("narrates", unit) == ()
    assert DOCSTRING_QUALITY.static_equivalents("contradicts", _unit()) == ()


@pytest.mark.parametrize(
    ("facts", "codes"),
    [
        ({"bare": True, "broad": False, "only_statement": "Pass"}, ("E722", "S110")),
        ({"bare": False, "broad": True, "only_statement": "Continue"}, ("BLE001", "S112")),
        ({"bare": False, "broad": True, "only_statement": "Return"}, ("BLE001",)),
        ({"bare": False, "broad": False, "only_statement": "Pass"}, ()),
    ],
)
def test_handler_facts_map_to_the_ruff_rules_that_fire_by_default(facts, codes):
    assert SILENT_FAILURE.static_equivalents("yes", _handler(**facts)) == codes


@pytest.mark.parametrize(
    ("question", "extra", "message"),
    [
        (Noul(instructions="q"), {"acceptable": frozenset({"yes"})}, "Noul rule has no labels"),
        (Noul(instructions="q"), {"actions": {"yes": "fix"}}, "Noul rule has no labels"),
        (
            Choice(instructions="q", criteria={"good": "g", "bad": "b"}),
            {"acceptable": frozenset({"good", "bad"})},
            "strict subset",
        ),
        (
            Choice(instructions="q", criteria={"good": "g", "bad": "b"}),
            {"acceptable": frozenset({"good"}), "actions": {"good": "keep"}},
            "actions must name flagged labels",
        ),
    ],
)
def test_rules_reject_labels_that_do_not_fit_their_question(question, extra, message):
    with pytest.raises(ValueError, match=message):
        Rule(id="r", kind="function", message="m", question=question, **extra)


def test_rule_ids_are_unique():
    assert len({rule.id for rule in RULES}) == len(RULES)


@pytest.mark.parametrize("rule", RULES, ids=lambda rule: rule.id)
def test_every_state_key_a_prompt_names_is_produced_for_its_unit_kind(rule):
    referenced = {re.split(r"[.\[]", name)[0] for name in re.findall(r"`([^`]+)`", rule.question.instructions)}
    assert referenced
    assert referenced <= STATE_KEYS[rule.kind]
