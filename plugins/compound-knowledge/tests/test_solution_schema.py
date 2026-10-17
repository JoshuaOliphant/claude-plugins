"""
ABOUTME: Validates solution files against the enums and rules in compound-capture's yaml-schema.md.
ABOUTME: Covers this repo's knowledge/solutions/ and the compound-retrieve eval fixture KBs, so schema and corpus can't drift apart.
"""

import datetime
import re
from pathlib import Path

import pytest
import yaml

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_ROOT.parent.parent
SCHEMA = PLUGIN_ROOT / "skills" / "compound-capture" / "references" / "yaml-schema.md"
EVALS = PLUGIN_ROOT / "skills" / "compound-retrieve" / "evals"
FIXTURES = EVALS / "fixtures"
KBS = [
    REPO_ROOT / "knowledge" / "solutions",
    FIXTURES / "solutions",
    *sorted((FIXTURES / "home").glob("**/knowledge/solutions")),
]
REQUIRED = [
    "title",
    "project",
    "date",
    "problem_type",
    "component",
    "solution_summary",
    "severity",
]
LEVELS = {"critical", "high", "medium", "low"}


def enum(field: str) -> set[str]:
    """The backticked first-column values of the schema's `## \\`field\\` Enum` table."""
    text = SCHEMA.read_text(encoding="utf-8")
    section = re.search(rf"^## `{field}` Enum.*?\n(.*?)(?=^---|^## |\Z)", text, re.M | re.S)
    return set(re.findall(r"^\| `([\w-]+)` \|", section.group(1), re.M))


def solution_files() -> list[tuple[Path, Path]]:
    return [
        (kb, path)
        for kb in KBS
        for path in sorted(kb.rglob("*.md"))
        if path.name != "critical-patterns.md"
    ]


def front_matter(path: Path) -> dict:
    match = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert match, f"{path} has no YAML front matter"
    return yaml.safe_load(match.group(1))


def problems(kb: Path, path: Path) -> list[str]:
    """Every rule in yaml-schema.md's Validation Rules that the file breaks."""
    meta = front_matter(path)
    found = [f"missing {field}" for field in REQUIRED if field not in meta]
    problem_type = meta.get("problem_type")
    principle = problem_type == "principles"
    for field in ("problem_type", "component", "root_cause", "resolution_type"):
        if field in meta and meta[field] not in enum(field):
            found.append(f"{field}: {meta[field]!r} is not in the schema's enum")
    if meta.get("severity") not in LEVELS:
        found.append(f"severity: {meta.get('severity')!r}")
    if problem_type in enum("problem_type"):
        folder = problem_type.replace("_", "-")
        if path.relative_to(kb).parts[0] != folder:
            found.append(f"problem_type {problem_type} belongs in {folder}/")
    if not principle and not 1 <= len(meta.get("symptoms") or []) <= 5:
        found.append("symptoms needs 1-5 entries")
    if len(meta.get("tags") or []) > 8:
        found.append("tags has more than 8 entries")
    if not isinstance(meta.get("date"), datetime.date):
        found.append(f"date: {meta.get('date')!r} is not YYYY-MM-DD")
    if principle:
        found += [f"principles need {f}" for f in ("statement", "confidence") if f not in meta]
        if "confidence" in meta and meta["confidence"] not in {"high", "medium", "low"}:
            found.append(f"confidence: {meta['confidence']!r}")
    related = meta.get("related_solutions") or []
    if len(related) > 5:
        found.append("related_solutions has more than 5 entries")
    own = path.relative_to(kb).as_posix()
    for link in related:
        target = kb / link
        if not re.fullmatch(r"[\w-]+/[\w.-]+\.md", link) or not target.is_file():
            found.append(f"related_solutions: {link} is not a solution in this KB")
        elif own not in (front_matter(target).get("related_solutions") or []):
            found.append(f"related_solutions: {link} does not link back")
    return found


@pytest.mark.parametrize(
    "kb, path",
    solution_files(),
    ids=lambda p: p.relative_to(REPO_ROOT).as_posix() if isinstance(p, Path) else str(p),
)
def test_solution_matches_schema(kb, path):
    assert problems(kb, path) == []


def test_every_kb_has_solutions():
    """A moved KB would leave the parametrized test above with nothing to check."""
    assert all(any(kb.rglob("*.md")) for kb in KBS)


@pytest.mark.parametrize("field", ["problem_type", "component", "root_cause", "resolution_type"])
def test_schema_enum_tables_parse(field):
    assert len(enum(field)) >= 5


def test_validator_catches_a_bad_file(tmp_path):
    bad = tmp_path / "patterns" / "bad.md"
    bad.parent.mkdir()
    bad.write_text(
        "---\ntitle: x\nproject: p\ndate: 2026-01-01\nproblem_type: workflow\n"
        "component: claude-code-plugins\nsolution_summary: s\nseverity: medium\n"
        "symptoms: [a]\nroot_cause: free text\n---\n",
        encoding="utf-8",
    )
    assert problems(tmp_path, bad) == [
        "component: 'claude-code-plugins' is not in the schema's enum",
        "root_cause: 'free text' is not in the schema's enum",
        "problem_type workflow belongs in workflow/",
    ]
