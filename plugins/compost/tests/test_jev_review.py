# ABOUTME: Tests the review Jev tools' gathering (git hunks, per-file diffs, canon openings, numbered lines) and
# ABOUTME: their decisions at each threshold's edge: skeptic-worthy findings, structural files, canon picks, located lines.
import asyncio

import pytest
from conftest import StubJev, choice, commit, noul, run_git, score
from jevtools import review
from jevtools.registry import BadInput

EXPORT_V1 = "".join(f"line {n}\n" for n in range(1, 21))
EXPORT_V2 = EXPORT_V1.replace("line 15\n", "line 15 changed\n")


@pytest.fixture
def repo(tmp_path):
    run_git(tmp_path, "init", "-q", "-b", "main")
    run_git(tmp_path, "config", "user.email", "t@example.com")
    run_git(tmp_path, "config", "user.name", "Tester")
    base = commit(tmp_path, {"app/export.py": EXPORT_V1, "app/old.py": "old\n"}, "first")
    run_git(tmp_path, "rm", "-q", "app/old.py")
    head = commit(tmp_path, {"app/export.py": EXPORT_V2, "app/cache.py": "STATE = {}\n"}, "add a cache")
    return {"path": tmp_path, "base": base, "head": head}


def severity(probabilities: dict[str, float], confidence: float) -> dict:
    return {
        "type": "choice",
        "choice": max(probabilities, key=probabilities.get),
        "probabilities": probabilities,
        "confidence": confidence,
    }


def serious(probability: float) -> dict[str, float]:
    return {"blocker": probability / 2, "major": probability / 2, "minor": 1 - probability, "not-a-finding": 0.0}


def test_hunk_around_picks_the_hunk_holding_the_line():
    diff = "diff --git a/x b/x\n@@ -1,2 +1,3 @@\n a\n+b\n c\n@@ -9 +10 @@\n-y\n+z\n"
    assert review.hunk_around(diff, 2).startswith("@@ -1,2 +1,3 @@")
    assert review.hunk_around(diff, 10) == "@@ -9 +10 @@\n-y\n+z\n"
    assert review.hunk_around(diff, 5) == ""
    assert review.hunk_around(diff, None) == diff


def test_gather_findings_extracts_the_hunk_from_the_diff_unless_one_is_given(repo):
    payload = {
        "repo": str(repo["path"]),
        "base": repo["base"],
        "head": repo["head"],
        "findings": [
            {"file": "app/export.py", "line": 15, "claim": "changed", "evidence": "line 15"},
            {"file": "app/export.py", "line": 1, "claim": "outside the diff"},
            {"file": "app/cache.py", "line": 1, "claim": "given", "hunk": "@@ given @@"},
        ],
    }
    changed, outside, given = review.gather_findings(payload)["findings"]
    assert "+line 15 changed" in changed["hunk"] and changed["evidence"] == "line 15"
    assert (outside["hunk"], outside["evidence"]) == ("", "")
    assert given["hunk"] == "@@ given @@"


def test_gather_findings_without_a_base_sends_no_hunk():
    gathered = review.gather_findings({"findings": [{"file": "a.py", "claim": "c"}]})
    assert gathered["findings"] == [{"file": "a.py", "line": None, "claim": "c", "evidence": "", "hunk": ""}]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "missing findings"),
        ({"findings": []}, "non-empty list"),
        ({"findings": [{"file": "a.py"}]}, "missing claim"),
        ({"findings": [{"file": "a.py", "claim": "c"}], "base": "no-such-ref"}, "git diff"),
    ],
)
def test_gather_findings_rejects_bad_input(payload, message):
    with pytest.raises(BadInput, match=message):
        review.gather_findings(payload)


@pytest.mark.parametrize(
    ("probabilities", "confidence", "worth"),
    [
        (serious(review.SKEPTIC_SEVERITY), 0.9, True),
        (serious(review.SKEPTIC_SEVERITY - 0.01), 0.9, False),
        (serious(0.1), review.SKEPTIC_CONFIDENCE - 0.01, True),
        (serious(0.1), review.SKEPTIC_CONFIDENCE, False),
    ],
    ids=["serious at the threshold", "serious just under", "unsure", "sure enough"],
)
def test_a_skeptic_is_worth_it_for_probable_blockers_and_majors_or_unsure_calls(probabilities, confidence, worth):
    jev = StubJev(lambda tool, state, questions: {"severity": severity(probabilities, confidence)})
    gathered = {"findings": [{"file": "a.py", "line": 3, "claim": "c", "evidence": "e", "hunk": "h"}]}
    result = asyncio.run(review.triage_finding(jev, gathered))
    [finding] = result["findings"]
    assert (finding["worth_skeptic"], result["skeptics"]) == (worth, int(worth))
    assert finding["severity"] == max(probabilities, key=probabilities.get)
    assert jev.calls[0][1] == {"finding": {"file": "a.py", "line": 3, "claim": "c", "evidence": "e"}, "hunk": "h"}


def test_gather_diff_lists_each_changed_file_with_its_status_and_diff(repo):
    gathered = review.gather_diff({"repo": str(repo["path"]), "base": repo["base"], "head": repo["head"]})
    statuses = {changed["file"]: changed["status"] for changed in gathered["files"]}
    assert statuses == {"app/cache.py": "added", "app/export.py": "modified", "app/old.py": "deleted"}
    assert "+STATE = {}" in gathered["files"][0]["diff"]


def test_gather_diff_needs_a_base_and_a_non_empty_diff(repo):
    with pytest.raises(BadInput, match="missing base"):
        review.gather_diff({})
    with pytest.raises(BadInput, match="is empty"):
        review.gather_diff({"repo": str(repo["path"]), "base": repo["head"], "head": repo["head"]})


def test_review_risk_ranks_files_and_flags_structural_ones_from_the_threshold():
    scores = {"a.py": review.STRUCTURAL - 0.01, "b.py": review.STRUCTURAL, "c.md": 0.2}
    jev = StubJev(lambda tool, state, questions: {"risk": score(scores[state["file"]], 5)})
    files = [{"file": name, "status": "modified", "diff": "d"} for name in scores]
    result = asyncio.run(review.review_risk(jev, {"files": files}))
    assert [(entry["file"], entry["structural"]) for entry in result["files"]] == [
        ("b.py", True),
        ("a.py", False),
        ("c.md", False),
    ]
    assert result["structural"] is True
    assert jev.calls[0][1]["changed_files"] == ["a.py", "b.py", "c.md"]


def test_essay_heads_reads_each_title_and_opening_paragraph_but_not_the_readme():
    heads = review.essay_heads(review.CANON)
    assert "README" not in heads
    assert heads["deep-modules"]["title"] == "Deep modules"
    assert heads["deep-modules"]["opening"].startswith("A deep module puts a lot of behavior behind a small interface.")
    assert "\n" not in heads["deep-modules"]["opening"]


def test_gather_change_takes_a_summary_or_summarizes_the_range(repo, tmp_path_factory):
    assert review.gather_change({"summary": "rename"})["change"] == "rename"
    summarized = review.gather_change({"repo": str(repo["path"]), "base": repo["base"], "head": repo["head"]})
    assert summarized["change"].startswith("add a cache")
    assert "+STATE = {}" in summarized["change"]
    with pytest.raises(BadInput, match="needs `summary` or `base`"):
        review.gather_change({})
    with pytest.raises(BadInput, match="no canon essays"):
        review.gather_change({"summary": "s", "canon": str(tmp_path_factory.mktemp("empty"))})


def picking(probabilities: dict[str, float]):
    def answer(tool, state, questions):
        return {"essay": {"type": "choice", "probabilities": probabilities, "confidence": 0.5}}

    return answer


def test_canon_pick_keeps_at_most_three_essays_at_or_above_the_threshold_and_never_none():
    essays = {stem: {"title": stem.title(), "opening": "o"} for stem in ["a", "b", "c", "d", "e"]}
    at, under = review.CANON_PICK, review.CANON_PICK - 0.01
    jev = StubJev(picking({"a": 0.3, "none": 0.25, "b": at, "c": 0.2, "d": 0.21, "e": under}))
    result = asyncio.run(review.canon_pick(jev, {"change": "c", "essays": essays}))
    assert [pick["essay"] for pick in result["essays"]] == ["a.md", "d.md", "c.md"]
    assert result["essays"][0] == {"essay": "a.md", "title": "A", "probability": 0.3}
    assert result["probabilities"]["e"] == round(under, 3)
    assert jev.calls[0][1] == {"change": "c"}
    assert jev.calls[0][2]["essay"].criteria["b"] == "B: o"

    quiet = StubJev(picking({"a": 0.05, "none": 0.8, "b": at, "c": 0.0, "d": 0.0, "e": under}))
    assert [
        pick["essay"] for pick in asyncio.run(review.canon_pick(quiet, {"change": "c", "essays": essays}))["essays"]
    ] == ["b.md"]


@pytest.fixture
def source(tmp_path):
    (tmp_path / "notes.md").write_text("".join(f"text {n}\n" for n in range(1, 8)))
    return tmp_path


def test_gather_queries_numbers_the_lines_of_a_file_or_a_range(source):
    [whole] = review.gather_queries({"repo": str(source), "claim": "c", "file": "notes.md"})["queries"]
    assert whole["lines"][0] == (1, "text 1") and len(whole["lines"]) == 7
    batch = review.gather_queries(
        {"repo": str(source), "queries": [{"claim": "c", "file": "notes.md", "start": 3, "end": 4}]}
    )
    assert batch["queries"][0]["lines"] == [(3, "text 3"), (4, "text 4")]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "needs `claim` and `file`"),
        ({"claim": "c", "file": "missing.md"}, "no such file"),
        ({"claim": "c", "file": "notes.md", "start": 9}, "no lines in 9..7"),
        ({"queries": [{"file": "notes.md"}]}, "missing claim"),
    ],
)
def test_gather_queries_rejects_bad_input(source, payload, message):
    with pytest.raises(BadInput, match=message):
        review.gather_queries({"repo": str(source), **payload})


def test_a_file_past_two_passes_must_be_narrowed_with_a_range(source, monkeypatch):
    monkeypatch.setattr(review, "CHOICE_LIMIT", 2)
    with pytest.raises(BadInput, match="too long to search"):
        review.gather_queries({"repo": str(source), "claim": "c", "file": "notes.md"})


LINES = [(number, f"text {number}") for number in range(1, 8)]


@pytest.mark.parametrize(("exists", "found"), [(review.FOUND, True), (review.FOUND - 0.01, False)])
def test_locate_picks_the_line_and_says_whether_the_file_addresses_the_claim(exists, found):
    def answer(tool, state, questions):
        return {"line": choice("L3", questions["line"].criteria, 0.7), "exists": noul(exists)}

    jev = StubJev(answer)
    result = asyncio.run(review.locate(jev, {"queries": [{"claim": "c", "file": "notes.md", "lines": LINES}]}))
    [location] = result["locations"]
    assert (location["line"], location["text"], location["probability"]) == (3, "text 3", 0.7)
    assert (location["exists"], location["found"]) == (round(exists, 3), found)
    assert [alternative["line"] for alternative in location["alternatives"]] == [1, 2]
    assert jev.calls[0][1]["document"].startswith("L1| text 1\nL2| text 2")


def test_locate_past_the_choice_limit_picks_a_window_then_a_line_in_it(monkeypatch):
    monkeypatch.setattr(review, "CHOICE_LIMIT", 3)

    def answer(tool, state, questions):
        if tool == "locate/window":
            return {"window": choice("L4-L6", questions["window"].criteria), "exists": noul(0.9)}
        assert "exists" not in questions
        return {"line": choice("L5", questions["line"].criteria)}

    jev = StubJev(answer)
    result = asyncio.run(review.locate(jev, {"queries": [{"claim": "c", "file": "notes.md", "lines": LINES}]}))
    assert list(jev.calls[0][2]["window"].criteria) == ["L1-L3", "L4-L6", "L7-L7"]
    assert jev.calls[1][1]["document"] == "L4| text 4\nL5| text 5\nL6| text 6"
    assert {key: result["locations"][0][key] for key in ("line", "exists", "found")} == {
        "line": 5,
        "exists": 0.9,
        "found": True,
    }
