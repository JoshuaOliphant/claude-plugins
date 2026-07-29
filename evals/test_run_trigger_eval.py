# ABOUTME: Unit tests for the trigger-eval fitness function (run_trigger_eval.py).
# ABOUTME: Uses the stub judge only — no network, no claude CLI, safe for CI.
from pathlib import Path

import pytest
from run_trigger_eval import (
    EVAL_TO_SKILL,
    EVALS_DIR,
    REPO_ROOT,
    evaluate_skill,
    parse_frontmatter_description,
    parse_judge_reply,
    score_split,
    split_cases,
    stub_judge,
)

PLAIN_SKILL = """---
name: my-skill
description: Does a thing when asked.
---
body
"""

FOLDED_SKILL = """---
name: my-skill
description: >-
  Does a thing
  across lines.
allowed-tools: [Read]
---
body
"""


def test_parse_plain_description():
    name, desc = parse_frontmatter_description(PLAIN_SKILL)
    assert (name, desc) == ("my-skill", "Does a thing when asked.")


def test_parse_folded_description():
    name, desc = parse_frontmatter_description(FOLDED_SKILL)
    assert (name, desc) == ("my-skill", "Does a thing across lines.")


def test_parse_rejects_missing_frontmatter():
    with pytest.raises(ValueError):
        parse_frontmatter_description("just a body")


def test_every_mapped_skill_parses():
    for eval_name, rel_path in EVAL_TO_SKILL.items():
        skill_md = (REPO_ROOT / rel_path).read_text()
        name, desc = parse_frontmatter_description(skill_md)
        assert desc, f"{eval_name}: empty description"
        assert (EVALS_DIR / f"{eval_name}-eval.json").exists()


def test_split_is_deterministic_and_partitions():
    cases = [{"query": f"query number {i}", "should_trigger": i % 2 == 0} for i in range(40)]
    dev1, holdout1 = split_cases(cases)
    dev2, holdout2 = split_cases(list(reversed(cases)))
    assert {c["query"] for c in dev1} == {c["query"] for c in dev2}
    assert len(dev1) + len(holdout1) == len(cases)
    assert dev1 and holdout1  # both splits non-empty at this size


def test_score_split_math():
    cases = [
        {"query": "a", "should_trigger": True},
        {"query": "b", "should_trigger": True},
        {"query": "c", "should_trigger": False},
        {"query": "d", "should_trigger": False},
    ]
    # one miss, one false positive
    scores = score_split(cases, [True, False, True, False])
    assert scores.tpr == 0.5
    assert scores.tnr == 0.5
    assert scores.fp_rate == 0.5
    assert scores.balanced_accuracy == 0.5


def test_parse_judge_reply_strips_fences_and_prose():
    reply = 'Sure!\n```json\n[true, false, true]\n```\n'
    assert parse_judge_reply(reply, 3) == [True, False, True]


def test_parse_judge_reply_rejects_wrong_arity():
    with pytest.raises(ValueError):
        parse_judge_reply("[true, false]", 3)


def test_evaluate_skill_end_to_end_with_stub(tmp_path: Path):
    eval_file = tmp_path / "fake-eval.json"
    eval_file.write_text(
        '[{"query": "use my-skill please", "should_trigger": true},'
        ' {"query": "unrelated request", "should_trigger": false}]'
    )
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(PLAIN_SKILL)
    result = evaluate_skill("bdd-spec", skill_file, stub_judge, eval_file=eval_file)
    assert result["skill_name"] == "my-skill"
    assert result["dev"]["n"] + result["holdout"]["n"] == 2
    for split in ("dev", "holdout"):
        assert 0.0 <= result[split]["balanced_accuracy"] <= 1.0
