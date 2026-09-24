# ABOUTME: Finds a repo's tests as node ids with their source, for Python (ast) and JS/TS (test/it calls).
# ABOUTME: The Jev test tools choose among these candidates; nothing here calls Jev.
import ast
import re
from pathlib import Path

SKIPPED = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
SOURCE_CHARS = 700
PYTHON_FILE = re.compile(r"^(test_.*|.*_test)\.py$")
JS_FILE = re.compile(r"\.(test|spec)\.(js|mjs|cjs|ts|tsx|jsx)$")
JS_TEST = re.compile(r"""^\s*(?:test|it)\s*\(\s*(['"`])(.+?)\1""")
JS_LINES = 15


def test_files(repo: Path) -> list[Path]:
    files = []
    for path in sorted(repo.rglob("*")):
        if SKIPPED & set(path.relative_to(repo).parts) or not path.is_file():
            continue
        if PYTHON_FILE.match(path.name) or JS_FILE.search(path.name):
            files.append(path)
    return files


def python_tests(path: Path, relative: str) -> dict[str, str]:
    source = path.read_text(errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    found = {}
    for node in tree.body:
        members = [(node, "")]
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            members = [(child, f"{node.name}::") for child in node.body]
        for member, prefix in members:
            if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef) and member.name.startswith("test_"):
                found[f"{relative}::{prefix}{member.name}"] = ast.get_source_segment(source, member)[:SOURCE_CHARS]
    return found


def js_tests(path: Path, relative: str) -> dict[str, str]:
    lines = path.read_text(errors="replace").splitlines()
    found = {}
    for number, line in enumerate(lines):
        if match := JS_TEST.match(line):
            found[f"{relative}::{match.group(2)}"] = "\n".join(lines[number : number + JS_LINES])[:SOURCE_CHARS]
    return found


def collect(repo: Path) -> dict[str, str]:
    tests: dict[str, str] = {}
    for path in test_files(repo):
        relative = str(path.relative_to(repo))
        tests.update(python_tests(path, relative) if path.suffix == ".py" else js_tests(path, relative))
    return tests
