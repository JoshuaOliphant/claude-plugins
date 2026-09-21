# ABOUTME: Tests for rules.py: how Noul and Choice answers become finding probabilities, and which units each rule applies to.
# ABOUTME: Answers are real SDK objects built by conftest helpers.
from conftest import choice, noul
from extract import Unit
from rules import COMMENT_KIND, DOCSTRING_QUALITY, RULES, SILENT_FAILURE, TEST_SMELL, TEST_WEAKENING


def _unit(kind="function", name="f", path="pkg/m.py", **state):
    return Unit(kind, path, 1, name, state)


def test_noul_rule_flags_on_yes_probability():
    assert SILENT_FAILURE.probability(noul(0.83)) == (0.83, "yes")


def test_choice_rule_sums_mass_outside_acceptable_and_names_top_problem():
    answer = choice(
        {
            "why": 0.4,
            "todo": 0.05,
            "narrates": 0.3,
            "section_banner": 0.2,
            "commented_out_code": 0.05,
            "change_history": 0.0,
            "misleading": 0.0,
        }
    )
    probability, label = COMMENT_KIND.probability(answer)
    assert round(probability, 2) == 0.55
    assert label == "narrates"


def test_docstring_rule_applies_only_with_a_docstring():
    assert DOCSTRING_QUALITY.applies(_unit(docstring="Doc."))
    assert not DOCSTRING_QUALITY.applies(_unit())


def test_test_smell_applies_to_test_functions_including_methods():
    assert TEST_SMELL.applies(_unit(name="TestOrders.test_total"))
    assert not TEST_SMELL.applies(_unit(name="total"))


def test_weakening_applies_to_test_paths_only():
    assert TEST_WEAKENING.applies(_unit(kind="hunk", path="tests/test_orders.py"))
    assert not TEST_WEAKENING.applies(_unit(kind="hunk", path="pkg/orders.py"))


def test_rules_without_a_filter_apply_to_every_unit_of_their_kind():
    assert SILENT_FAILURE.applies(_unit(kind="handler"))


def test_rule_ids_are_unique_and_choice_rules_name_real_labels():
    assert len({rule.id for rule in RULES}) == len(RULES)
    for rule in RULES:
        if rule.acceptable:
            assert rule.acceptable <= set(rule.question.criteria)
