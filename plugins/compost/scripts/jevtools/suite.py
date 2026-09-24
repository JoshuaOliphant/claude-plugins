# ABOUTME: Finds a repo's tests as node ids with their source, for Python (ast) and JS/TS (test/it calls),
# ABOUTME: in the working tree or at a git revision. The Jev test tools choose among these; nothing here calls Jev.
import ast
import re
import subprocess
from pathlib import Path

SKIPPED = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
SOURCE_CHARS = 700
PYTHON_FILE = re.compile(r"^(test_.*|.*_test)\.py$")
JS_FILE = re.compile(r"\.(test|spec)\.(js|mjs|cjs|ts|tsx|jsx)$")
JS_TEST = re.compile(r"""^\s*(?:test|it)\s*\(\s*(['"`])(.+?)\1""")
JS_LINES = 15


def is_test_file(relative: str) -> bool:
    parts = Path(relative).parts
    if SKIPPED & set(parts):
        return False
    return bool(PYTHON_FILE.match(parts[-1]) or JS_FILE.search(parts[-1]))


def test_files(repo: Path) -> list[Path]:
    return [path for path in sorted(repo.rglob("*")) if path.is_file() and is_test_file(str(path.relative_to(repo)))]


def dedent(line: str, indent: int) -> str:
    return line[indent:] if line[:indent].isspace() else line


def python_tests(source: str, relative: str, limit: int) -> dict[str, str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    lines = source.splitlines()
    found = {}
    for node in tree.body:
        members = [(node, "")]
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            members = [(child, f"{node.name}::") for child in node.body]
        for member, prefix in members:
            if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef) and member.name.startswith("test_"):
                start = min([member.lineno, *(decorator.lineno for decorator in member.decorator_list)])
                text = "\n".join(dedent(line, member.col_offset) for line in lines[start - 1 : member.end_lineno])
                found[f"{relative}::{prefix}{member.name}"] = text[:limit]
    return found


def js_tests(source: str, relative: str, limit: int) -> dict[str, str]:
    lines = source.splitlines()
    found = {}
    for number, line in enumerate(lines):
        if match := JS_TEST.match(line):
            found[f"{relative}::{match.group(2)}"] = "\n".join(lines[number : number + JS_LINES])[:limit]
    return found


def tests_in(relative: str, source: str, limit: int = SOURCE_CHARS) -> dict[str, str]:
    reader = python_tests if relative.endswith(".py") else js_tests
    return reader(source, relative, limit)


def collect(repo: Path, limit: int = SOURCE_CHARS) -> dict[str, str]:
    tests: dict[str, str] = {}
    for path in test_files(repo):
        tests.update(tests_in(str(path.relative_to(repo)), path.read_text(errors="replace"), limit))
    return tests


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)


def collect_at(repo: Path, ref: str, limit: int = SOURCE_CHARS) -> dict[str, str]:
    """The tests under `repo` as they were at `ref`; paths are relative to `repo`, as `collect` gives them."""
    if git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode != 0:
        raise LookupError(f"{ref!r} is not a commit in {repo}")
    listed = git(repo, "ls-tree", "-r", "--name-only", ref).stdout.splitlines()
    tests: dict[str, str] = {}
    for relative in filter(is_test_file, listed):
        tests.update(tests_in(relative, git(repo, "show", f"{ref}:./{relative}").stdout, limit))
    return tests
