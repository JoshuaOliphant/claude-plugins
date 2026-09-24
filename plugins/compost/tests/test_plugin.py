# ABOUTME: Checks the plugin as shipped: frontmatter, links, compost:<name> and ${CLAUDE_PLUGIN_ROOT} references,
# ABOUTME: pile.toml feeds and NOTICE, and that git tracks every shipped file. Runs on the real files.
import os
import re
import subprocess

import pile
import pytest
import yaml
from conftest import PLUGIN_ROOT

LOCAL_ONLY = {"tests", ".venv", ".pytest_cache", "__pycache__"}
SHIPPED = (
    ".claude-plugin",
    "agents",
    "canon",
    "hooks",
    "scripts",
    "skills",
    "workflows",
    "NOTICE",
    "pile.toml",
    "README.md",
)
SKILLS = sorted(path.parent for path in (PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
MARKDOWN = sorted(
    path for path in PLUGIN_ROOT.rglob("*.md") if not LOCAL_ONLY & set(path.relative_to(PLUGIN_ROOT).parts)
)
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
REFERENCE = re.compile(r"compost:([a-z][a-z0-9-]*)")
PLUGIN_PATH = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+[\w/])")
WORKFLOW_NAME = re.compile(r"export const meta = \{\s*name: '([^']+)'")


def frontmatter(skill_dir):
    text = (skill_dir / "SKILL.md").read_text()
    assert text.startswith("---\n"), f"{skill_dir.name}: SKILL.md must open with frontmatter"
    return yaml.safe_load(text[4 : text.index("\n---", 4)])


def known_names():
    workflows = {WORKFLOW_NAME.search(path.read_text()).group(1) for path in (PLUGIN_ROOT / "workflows").glob("*.js")}
    agents = {path.stem for path in (PLUGIN_ROOT / "agents").glob("*.md")}
    return {path.name for path in SKILLS} | workflows | agents


@pytest.mark.parametrize("skill_dir", SKILLS, ids=lambda path: path.name)
def test_skill_frontmatter_names_its_directory_and_says_when_to_use_it(skill_dir):
    fields = frontmatter(skill_dir)
    assert fields["name"] == skill_dir.name
    assert re.search(r"\bUse (when|before|once|after)\b", fields["description"])
    assert len(fields["description"]) <= 1024


@pytest.mark.parametrize("document", MARKDOWN, ids=lambda path: str(path.relative_to(PLUGIN_ROOT)))
def test_relative_links_resolve(document):
    targets = [target for target in LINK.findall(document.read_text()) if "://" not in target]
    missing = [target for target in targets if not (document.parent / target).exists()]
    assert missing == []


def test_every_compost_reference_names_a_skill_workflow_or_agent():
    names = known_names()
    files = [*MARKDOWN, *(PLUGIN_ROOT / "workflows").glob("*.js")]
    unknown = {
        (str(path.relative_to(PLUGIN_ROOT)), name)
        for path in files
        for name in REFERENCE.findall(path.read_text())
        if name not in names
    }
    assert unknown == set()


def test_pile_feeds_only_existing_skills_or_the_canon_and_notice_is_current():
    sources = pile.load(PLUGIN_ROOT / "pile.toml")
    targets = {path.name for path in SKILLS} | {"canon"}
    fed = {skill for source in sources for skills in source.feeds.values() for skill in skills}
    assert fed - targets == set()
    assert (PLUGIN_ROOT / "NOTICE").read_text() == pile.render_notice(sources)


def test_plugin_root_paths_exist_and_scripts_are_executable():
    referenced = {path for document in MARKDOWN for path in PLUGIN_PATH.findall(document.read_text())}
    assert referenced, "no ${CLAUDE_PLUGIN_ROOT} paths found; the pattern no longer matches the skills"
    assert sorted(path for path in referenced if not (PLUGIN_ROOT / path).exists()) == []
    scripts = sorted(PLUGIN_ROOT.glob("skills/*/scripts/*.sh"))
    assert [script.name for script in scripts if not os.access(script, os.X_OK)] == []


def test_git_ignores_no_shipped_file():
    ignored = subprocess.run(
        ["git", "-C", str(PLUGIN_ROOT), "ls-files", "--others", "--ignored", "--exclude-standard", *SHIPPED],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\n")
    assert [path for path in ignored if path and not LOCAL_ONLY & set(path.split("/"))] == []
