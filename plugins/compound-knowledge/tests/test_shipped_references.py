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
    ],
)
def test_path_readers_delegate_to_the_resolver(doc):
    assert "scripts/resolve_paths.py" in (PLUGIN_ROOT / doc).read_text(encoding="utf-8")
