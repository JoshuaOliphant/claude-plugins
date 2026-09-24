# ABOUTME: Tests the meta family's gatherers (upstream diffs, skill descriptions, markdown passages, final messages)
# ABOUTME: and the thresholds each judge applies to Jev's answers: classify-change, route, rulings-lint, stop-guard.
import asyncio

import pytest
from conftest import PLUGIN_ROOT, StubJev, commit, noul, run_git
from jevtools import meta
from jevtools.registry import TOOLS, BadInput


def choice_of(probabilities: dict[str, float]) -> dict:
    chosen = max(probabilities, key=probabilities.get)
    return {"type": "choice", "choice": chosen, "probabilities": probabilities, "confidence": probabilities[chosen]}


@pytest.fixture
def plugin(tmp_path):
    root = tmp_path / "plugin"
    (root / "skills" / "spec").mkdir(parents=True)
    (root / "skills" / "spec" / "SKILL.md").write_text(
        "---\nname: spec\ndescription: Turns a fuzzy idea into a spec. Use when asked to spec it out.\n---\n\n# spec\n"
    )
    (root / "skills" / "draft").mkdir()
    (root / "skills" / "draft" / "SKILL.md").write_text("# draft, no frontmatter yet\n")
    (root / "canon").mkdir()
    (root / "canon" / "README.md").write_text(
        "# Canon\n\nShort essays on the ideas compost's skills lean on, one per file.\n"
    )
    return root


def test_meta_registers_its_four_tools():
    assert {"classify-change", "route", "rulings-lint", "stop-guard"} <= set(TOOLS)


def test_skill_descriptions_skip_skills_without_one_and_texts_read_the_canon_readme(plugin):
    assert meta.skill_descriptions(plugin) == {"spec": "Turns a fuzzy idea into a spec. Use when asked to spec it out."}
    texts = meta.skill_texts(["spec", "canon", "gone"], plugin)
    assert sorted(texts) == ["canon", "spec"]
    assert texts["canon"].startswith("# Canon")


def test_gather_changes_diffs_each_path_from_the_pin_to_upstream_head(upstream, pile_file):
    commit(upstream, {"skills/to-spec/SKILL.md": "spec v2\n"}, "sharpen to-spec")
    payload = {"source": "acme", "paths": ["skills/to-spec/SKILL.md", "README.md"], "pile": str(pile_file)}
    gathered = meta.gather_changes(payload)
    spec_change, readme = gathered["changes"]
    assert (spec_change["path"], spec_change["skills"]) == ("skills/to-spec/SKILL.md", ["spec"])
    assert "+spec v2" in spec_change["diff"]
    assert (readme["skills"], readme["diff"]) == ([], "")
    assert gathered["source"] == "acme"
    assert list(gathered["skills"]) == ["spec"]
    assert "implement" in gathered["catalog"]

    first = run_git(upstream, "rev-list", "--max-parents=0", "HEAD")
    again = meta.gather_changes(payload | {"head": first})
    assert [change["diff"] for change in again["changes"]] == ["", ""]


def test_describe_changes_cuts_long_diffs(monkeypatch):
    monkeypatch.setattr(meta, "DIFF_CHARS", 5)
    described = meta.describe_changes("acme", [{"path": "a", "skills": [], "diff": "0123456789"}])
    assert described["changes"] == [{"path": "a", "skills": [], "diff": "01234"}]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"paths": ["a"]}, "missing source"),
        ({"source": "acme", "paths": []}, "`paths` is empty"),
        ({"source": "nobody", "paths": ["a"]}, "no source named 'nobody'"),
        ({"source": "acme", "paths": ["a"], "pin": "0" * 40}, "failed"),
    ],
    ids=["no source", "no paths", "unknown source", "pin not upstream"],
)
def test_gather_changes_turns_bad_input_and_git_failures_into_bad_input(pile_file, payload, message):
    with pytest.raises(BadInput, match=message):
        meta.gather_changes(payload | {"pile": str(pile_file)})


def classifying(probabilities: dict[str, float]):
    def answer(tool, state, questions):
        return {"verdict": choice_of(probabilities)}

    return answer


@pytest.mark.parametrize(
    ("probabilities", "verdict", "needs_reading"),
    [
        ({"adopt": 0.1, "adapt": 0.3, "ignore": 0.6}, "ignore", False),
        ({"adopt": 0.11, "adapt": 0.3, "ignore": 0.59}, "ignore", True),
        ({"adopt": 0.9, "adapt": 0.05, "ignore": 0.05}, "adopt", True),
        ({"adopt": 0.05, "adapt": 0.9, "ignore": 0.05}, "adapt", True),
    ],
    ids=["confident ignore is recorded", "unsure ignore is read", "adopt is read", "adapt is read"],
)
def test_classify_change_records_only_confident_ignores(probabilities, verdict, needs_reading):
    gathered = {
        "source": "acme",
        "changes": [{"path": "skills/to-spec/SKILL.md", "skills": ["spec"], "diff": "+spec v2"}],
        "skills": {"spec": "spec text"},
        "catalog": {"spec": "spec description"},
    }
    jev = StubJev(classifying(probabilities))
    result = asyncio.run(meta.classify_change(jev, gathered))
    [change] = result["changes"]
    assert (change["verdict"], change["needs_reading"]) == (verdict, needs_reading)
    assert change["probabilities"] == probabilities
    assert result["to_read"] == (["skills/to-spec/SKILL.md"] if needs_reading else [])
    tool, state, questions = jev.calls[0]
    assert (tool, state["compost_skills"], state["rulings"]) == ("classify-change", {"spec": "spec text"}, meta.RULINGS)
    assert set(questions["verdict"].criteria) == {"adopt", "adapt", "ignore"}


def test_an_unchanged_path_is_ignored_without_asking_jev():
    gathered = {
        "source": "acme",
        "changes": [{"path": "README.md", "skills": [], "diff": "\n"}],
        "skills": {},
        "catalog": {},
    }
    jev = StubJev(classifying({"ignore": 1.0}))
    result = asyncio.run(meta.classify_change(jev, gathered))
    assert result["changes"][0] | {"skills": None} == {
        "path": "README.md",
        "skills": None,
        "verdict": "ignore",
        "confidence": 1.0,
        "probabilities": {},
        "needs_reading": False,
    }
    assert jev.calls == []


def test_gather_route_takes_one_prompt_or_many_and_needs_skills(plugin, tmp_path):
    assert meta.gather_route({"prompt": "spec this out", "plugin": str(plugin)})["prompts"] == ["spec this out"]
    gathered = meta.gather_route({"prompts": ["a", "b"]})
    assert gathered["prompts"] == ["a", "b"]
    assert gathered["skills"] == meta.skill_descriptions(PLUGIN_ROOT)
    with pytest.raises(BadInput, match="needs `prompt` or `prompts`"):
        meta.gather_route({"prompts": []})
    with pytest.raises(BadInput, match="no skills"):
        meta.gather_route({"prompt": "x", "plugin": str(tmp_path)})


@pytest.mark.parametrize(
    ("close_margin", "close"), [(0.5, False), (0.5000001, True)], ids=["at margin", "under margin"]
)
def test_route_picks_the_top_skill_and_marks_close_calls(monkeypatch, close_margin, close):
    monkeypatch.setattr(meta, "CLOSE_MARGIN", close_margin)
    jev = StubJev(lambda tool, state, questions: {"skill": choice_of({"spec": 0.75, "none": 0.25})})
    result = asyncio.run(meta.route(jev, {"prompts": ["spec this out"], "skills": {"spec": "Turns ideas into specs."}}))
    assert result["routes"] == [
        {
            "prompt": "spec this out",
            "skill": "spec",
            "margin": 0.5,
            "close": close,
            "probabilities": {"spec": 0.75, "none": 0.25},
        }
    ]
    tool, state, questions = jev.calls[0]
    assert (tool, state) == ("route", {"request": "spec this out"})
    assert list(questions["skill"].criteria) == ["spec", "none"]


def test_passages_split_on_blank_lines_and_list_items_and_keep_code_fences_whole(tmp_path):
    source = tmp_path / "SKILL.md"
    source.write_text(
        "# spec\n\nShort.\n\n## Steps\n\n1. **Ask in rounds** until no open decisions remain, then write the spec.\n"
        "2. **Post the parent issue** with the tracker the repo records, labeled spec.\n\n"
        "   ```bash\n   # not a heading\n\n   gh issue create --label spec\n   ```\n"
    )
    units = meta.passages(source, "skills/spec/SKILL.md")
    assert [(unit["line"], unit["heading"]) for unit in units] == [(7, "Steps"), (8, "Steps"), (10, "Steps")]
    assert units[2]["text"].splitlines()[1:3] == ["   # not a heading", ""]
    assert units[0]["user_in_the_loop"] == meta.USER_IN_THE_LOOP["skills/spec/"]
    assert meta.passage("skills/build/SKILL.md", 1, "", "text")["user_in_the_loop"] is None


def test_gather_passages_lints_skills_canon_agents_and_readme_by_default(plugin):
    (plugin / "README.md").write_text("compost is one software-engineering workflow made from several skill sets.\n")
    gathered = meta.gather_passages({"plugin": str(plugin)})
    assert [unit["file"] for unit in gathered["passages"]] == ["skills/spec/SKILL.md", "canon/README.md", "README.md"]
    chosen = meta.gather_passages({"plugin": str(plugin), "paths": ["README.md"]})
    assert [unit["file"] for unit in chosen["passages"]] == ["README.md"]


def test_gather_passages_rejects_missing_files_and_empty_text(plugin):
    with pytest.raises(BadInput, match="no such file: gone.md"):
        meta.gather_passages({"plugin": str(plugin), "paths": ["gone.md"]})
    with pytest.raises(BadInput, match="no passages"):
        meta.gather_passages({"plugin": str(plugin), "paths": ["skills/draft/SKILL.md"]})


def linting(scores: dict[str, dict[str, float]]):
    def answer(tool, state, questions):
        chosen = scores.get(state["passage"]["text"], {})
        return {name: noul(chosen.get(name, 0.0)) for name in questions}

    return answer


def unit(text: str) -> dict:
    return meta.passage("skills/build/SKILL.md", 3, "Steps", text)


@pytest.mark.parametrize(
    ("rule", "answers", "flagged"),
    [
        ("unallowed_stop", {"gate": 0.9, "allowed": 0.5}, True),
        ("unallowed_stop", {"gate": 0.89, "allowed": 0.5}, False),
        ("tdd_ritual", {"tdd_ritual": 0.7}, True),
        ("tdd_ritual", {"tdd_ritual": 0.69}, False),
        ("redaction", {"redaction": 0.5}, True),
        ("redaction", {"redaction": 0.49}, False),
    ],
    ids=["stop at", "stop under", "ritual at", "ritual under", "redaction at", "redaction under"],
)
def test_rulings_lint_flags_a_passage_at_its_rules_threshold(rule, answers, flagged):
    text = "Wait for the user to approve the plan before writing any code at all."
    jev = StubJev(linting({text: answers}))
    result = asyncio.run(meta.rulings_lint(jev, {"passages": [unit(text)]}))
    assert result["passages"] == 1
    assert bool(result["flags"][rule]) == flagged
    assert result["flagged"] == int(flagged)
    tool, state, questions = jev.calls[0]
    assert (tool, state["policy"]) == ("rulings-lint", meta.POLICY)
    assert set(questions) == {"gate", "allowed", *meta.RULES}


def test_rulings_lint_lists_flags_strongest_first_with_a_short_excerpt(monkeypatch):
    monkeypatch.setattr(meta, "EXCERPT", 12)
    weak, strong = "Redact tokens before you paste a log.", "Redact every secret before showing output."
    jev = StubJev(linting({weak: {"redaction": 0.6}, strong: {"redaction": 0.95}}))
    result = asyncio.run(meta.rulings_lint(jev, {"passages": [unit(weak), unit(strong)]}))
    assert result["flags"]["redaction"] == [
        {
            "file": "skills/build/SKILL.md",
            "line": 3,
            "heading": "Steps",
            "excerpt": "Redact every",
            "probability": 0.95,
        },
        {"file": "skills/build/SKILL.md", "line": 3, "heading": "Steps", "excerpt": "Redact token", "probability": 0.6},
    ]


def test_gather_stop_needs_a_message_and_keeps_its_end(monkeypatch):
    monkeypatch.setattr(meta, "MESSAGE_CHARS", 8)
    assert meta.gather_stop({"message": "  report... Which one?  "}) == {"message": "ich one?"}
    with pytest.raises(BadInput, match="missing message"):
        meta.gather_stop({})
    with pytest.raises(BadInput, match="`message` is empty"):
        meta.gather_stop({"message": "   "})


@pytest.mark.parametrize(
    ("waits", "allowed", "block"),
    [(1.0, 0.5, True), (0.99, 0.5, False), (0.95, 0.9, False)],
    ids=["waits, not allowed: at threshold", "just under threshold", "waits on an allowed stop"],
)
def test_stop_guard_blocks_a_wait_outside_the_allowed_stops(waits, allowed, block):
    jev = StubJev(lambda tool, state, questions: {"waits": noul(waits), "allowed": noul(allowed)})
    result = asyncio.run(meta.stop_guard(jev, {"message": "Which library do you prefer?"}))
    assert result == {"block": block, "score": round(waits * (1 - allowed), 3), "waits": waits, "allowed": allowed}
    tool, state, _ = jev.calls[0]
    assert (tool, state["allowed_stops"], state["message"]) == (
        "stop-guard",
        meta.ALLOWED_STOPS,
        "Which library do you prefer?",
    )
