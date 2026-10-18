"""
ABOUTME: Tests that every references/*.md file a skill, command, or agent names is shipped by the plugin.
ABOUTME: Also fails on any symlink in the plugin whose target is missing.
"""

import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REFERENCE = re.compile(r"`(\$\{CLAUDE_PLUGIN_ROOT\}/)?((?:[\w.-]+/)*references/[\w.-]+\.md)`")
INSTRUCTION_DOCS = sorted(
    path
    for folder in ("skills", "commands", "agents")
    for path in (PLUGIN_ROOT / folder).rglob("*.md")
    if path.is_file()
)


def named_references(doc: Path) -> list[Path]:
    """Each backticked references/ path in the doc, resolved against the plugin root or the doc's directory."""
    paths = []
    for plugin_rooted, ref in REFERENCE.findall(doc.read_text(encoding="utf-8")):
        base = PLUGIN_ROOT if plugin_rooted else doc.parent
        paths.append(base / ref)
    return paths


@pytest.mark.parametrize(
    "doc", INSTRUCTION_DOCS, ids=lambda p: p.relative_to(PLUGIN_ROOT).as_posix()
)
def test_every_named_reference_is_shipped(doc):
    missing = [
        str(path.relative_to(PLUGIN_ROOT)) for path in named_references(doc) if not path.is_file()
    ]
    assert missing == []


def test_no_dangling_symlinks():
    dangling = [
        str(path.relative_to(PLUGIN_ROOT))
        for path in PLUGIN_ROOT.rglob("*")
        if path.is_symlink() and not path.exists()
    ]
    assert dangling == []


@pytest.mark.parametrize(
    "doc",
    [doc for doc in INSTRUCTION_DOCS if doc != PLUGIN_ROOT / "commands" / "setup.md"],
    ids=lambda p: p.relative_to(PLUGIN_ROOT).as_posix(),
)
def test_only_setup_names_the_config_file(doc):
    """Readers take paths from scripts/resolve_paths.py; only setup, which writes the config, names it."""
    text = doc.read_text(encoding="utf-8")
    assert "compound-knowledge.local.md" not in text
    assert "first match" not in text.lower()


@pytest.mark.parametrize(
    "doc",
    [
        "skills/compound-capture/SKILL.md",
        "skills/compound-retrieve/SKILL.md",
        "agents/knowledge-researcher.md",
        "commands/setup.md",
    ],
)
def test_path_readers_delegate_to_the_resolver(doc):
    assert "scripts/resolve_paths.py" in (PLUGIN_ROOT / doc).read_text(encoding="utf-8")


def test_setup_writes_write_path_not_the_alias():
    """setup writes the key the resolver prefers, so its config can't be shadowed by its own alias."""
    text = (PLUGIN_ROOT / "commands" / "setup.md").read_text(encoding="utf-8")
    config_keys = re.findall(r"^\s*(\w+)\s*:", text, re.MULTILINE)
    assert "write_path" in config_keys
    assert "solutions_path" not in config_keys


def test_setup_can_edit_an_existing_config_in_place():
    """setup keeps a config's other keys when it changes write_path, which needs the Edit tool."""
    front_matter = (
        (PLUGIN_ROOT / "commands" / "setup.md").read_text(encoding="utf-8").split("---")[1]
    )
    assert "Edit" in front_matter


CORPUS_PLACEHOLDER = re.compile(r"\{(?:write|read)_path\}|\bread_paths\b")
SEARCH_VERB = re.compile(r"\b(?:grep|glob|search|scan)", re.IGNORECASE)
KNOWN_CORPUS_READERS = {
    "skills/compound-capture/SKILL.md",
    "skills/compound-capture/references/registry-format.md",
    "skills/compound-retrieve/SKILL.md",
    "skills/compound-graduate/SKILL.md",
    "skills/compound-graduate/references/garden-workflow.md",
    "skills/compound-graduate/references/promote-workflow.md",
    "agents/knowledge-researcher.md",
}


def names_and_searches_corpus(text: str) -> bool:
    """True when the text names a corpus path placeholder and uses a search verb (Grep, Glob, search, scan)."""
    return bool(CORPUS_PLACEHOLDER.search(text) and SEARCH_VERB.search(text))


def corpus_readers() -> list[Path]:
    """Instruction docs that name the corpus paths and search them; setup only writes the config."""
    readers = []
    for doc in INSTRUCTION_DOCS:
        if doc == PLUGIN_ROOT / "commands" / "setup.md":
            continue
        if names_and_searches_corpus(doc.read_text(encoding="utf-8")):
            readers.append(doc)
    return readers


def test_detector_flags_read_paths_without_the_path_keyword():
    assert names_and_searches_corpus("Scan every entry in `read_paths` for candidates.")
    assert not names_and_searches_corpus("Write the config key `write_path`.")
    assert not names_and_searches_corpus("Grep the repo for TODOs.")


def test_corpus_search_detector_finds_the_known_readers():
    """Guards the guard: a detector that matches nothing would pass the archive check vacuously."""
    found = {doc.relative_to(PLUGIN_ROOT).as_posix() for doc in corpus_readers()}
    assert KNOWN_CORPUS_READERS <= found


@pytest.mark.parametrize(
    "doc", corpus_readers(), ids=lambda p: p.relative_to(PLUGIN_ROOT).as_posix()
)
def test_every_corpus_reader_skips_the_archive(doc):
    """Garden moves retired solutions to {write_path}/_archive/, which only works if every reader skips it."""
    assert "_archive/" in doc.read_text(encoding="utf-8")
