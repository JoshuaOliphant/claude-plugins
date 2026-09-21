# ABOUTME: Turns Python source and unified diffs into lintable units: comments, except handlers, functions, log calls, hunks.
# ABOUTME: Pure stdlib (ast, tokenize); each unit carries the state Jev needs to judge it.

import ast
import io
import re
import tokenize
from dataclasses import dataclass, field

CONTEXT_LINES = 3
MAX_SEGMENT_LINES = 80

DIRECTIVE = re.compile(
    r"^#(!|\s*(ABOUTME:|-\*-|noqa|type:|pragma|pyright:|ruff:|fmt:|mypy:|isort:|pylint:))"
)
SCRIPT_BLOCK_START = "# /// script"
SCRIPT_BLOCK_END = "# ///"
BROAD_EXCEPTIONS = {"Exception", "BaseException"}
LOG_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "log"}


@dataclass(frozen=True)
class Unit:
    kind: str
    path: str
    line: int
    name: str
    state: dict = field(hash=False)
    facts: dict = field(default_factory=dict, hash=False)


def is_test_path(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return name.startswith("test_") or name.endswith("_test.py") or "/tests/" in f"/{path}"


def truncate(text: str, max_lines: int = MAX_SEGMENT_LINES) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[:max_lines] + [f"... ({len(lines) - max_lines} more lines)"])


def _comment_tokens(source: str) -> list[tokenize.TokenInfo]:
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return [token for token in tokens if token.type == tokenize.COMMENT]


def _code_neighbors(lines: list[str], first: int, last: int) -> tuple[str, str]:
    before, after = [], []
    row = first - 1
    while row >= 1 and len(before) < CONTEXT_LINES:
        if not lines[row - 1].lstrip().startswith("#"):
            before.insert(0, lines[row - 1])
        row -= 1
    row = last + 1
    while row <= len(lines) and len(after) < CONTEXT_LINES:
        if not lines[row - 1].lstrip().startswith("#"):
            after.append(lines[row - 1])
        row += 1
    return "\n".join(before), "\n".join(after)


def extract_comments(path: str, source: str) -> list[Unit]:
    lines = source.splitlines()
    blocks: list[list[tokenize.TokenInfo]] = []
    in_script_block = False
    for token in _comment_tokens(source):
        text = token.string.strip()
        if text == SCRIPT_BLOCK_START:
            in_script_block = True
            continue
        if in_script_block:
            in_script_block = text != SCRIPT_BLOCK_END
            continue
        if DIRECTIVE.match(text):
            continue
        row, col = token.start
        inline = bool(lines[row - 1][:col].strip())
        previous = blocks[-1][-1] if blocks else None
        continues_block = (
            previous is not None
            and not inline
            and previous.start[0] == row - 1
            and not lines[previous.start[0] - 1][: previous.start[1]].strip()
        )
        if continues_block:
            blocks[-1].append(token)
        else:
            blocks.append([token])

    units = []
    for block in blocks:
        first, last = block[0].start[0], block[-1].start[0]
        before, after = _code_neighbors(lines, first, last)
        head_line = lines[first - 1]
        inline_code = head_line[: block[0].start[1]].rstrip()
        state = {
            "comment": "\n".join(token.string for token in block),
            "code_before": before,
            "code_after": after,
        }
        if inline_code.strip():
            state["inline_code"] = inline_code
        units.append(Unit("comment", path, first, block[0].string.strip()[:60], state))
    return units


def _segment(source: str, node: ast.AST) -> str:
    return truncate(ast.get_source_segment(source, node) or "")


def _is_logger(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return "log" in node.id.lower()
    if isinstance(node, ast.Attribute):
        return "log" in node.attr.lower()
    return False


class _Collector(ast.NodeVisitor):
    def __init__(self, path: str, source: str):
        self.path = path
        self.source = source
        self.scope: list[str] = []
        self.functions: list[ast.AST] = []
        self.units: list[Unit] = []

    def _visit_scope(self, node, name: str) -> None:
        self.scope.append(name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_scope(node, node.name)

    def _visit_function(self, node) -> None:
        qualified = ".".join([*self.scope, node.name])
        state = {"qualified_name": qualified, "function": _segment(self.source, node)}
        docstring = ast.get_docstring(node)
        if docstring:
            state["docstring"] = docstring
        self.units.append(Unit("function", self.path, node.lineno, qualified, state))
        self.functions.append(node)
        self._visit_scope(node, node.name)
        self.functions.pop()

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_Try(self, node: ast.Try) -> None:
        statement = _segment(self.source, node)
        for handler in node.handlers:
            state = {"try_statement": statement, "handler": _segment(self.source, handler)}
            name = ast.unparse(handler.type) if handler.type else "bare except"
            facts = {
                "bare": handler.type is None,
                "broad": name in BROAD_EXCEPTIONS,
                "only_statement": (
                    type(handler.body[0]).__name__ if len(handler.body) == 1 else None
                ),
            }
            self.units.append(Unit("handler", self.path, handler.lineno, name, state, facts))
        self.generic_visit(node)

    visit_TryStar = visit_Try

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in LOG_METHODS and _is_logger(func.value):
            state = {"log_call": _segment(self.source, node)}
            if self.functions:
                state["enclosing_function"] = _segment(self.source, self.functions[-1])
            self.units.append(Unit("log_call", self.path, node.lineno, func.attr, state))
        self.generic_visit(node)


def extract_source_units(path: str, source: str) -> list[Unit]:
    collector = _Collector(path, source)
    collector.visit(ast.parse(source))
    return extract_comments(path, source) + collector.units


HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def extract_hunks(diff: str) -> list[Unit]:
    units = []
    path = None
    hunk: dict | None = None

    def close() -> None:
        if hunk and (hunk["removed"] or hunk["added"]):
            state = {
                "path": path,
                "hunk": truncate("\n".join(hunk["lines"])),
                "removed": "\n".join(hunk["removed"]),
                "added": "\n".join(hunk["added"]),
            }
            units.append(Unit("hunk", path, hunk["start"], path, state))

    for line in diff.splitlines():
        if line.startswith("+++ "):
            close()
            hunk = None
            target = line[4:]
            path = target.removeprefix("b/")
        elif line.startswith("@@"):
            close()
            match = HUNK_HEADER.match(line)
            hunk = {"start": int(match.group(1)), "lines": [], "removed": [], "added": []}
        elif hunk is not None and not line.startswith(("--- ", "diff ", "index ")):
            hunk["lines"].append(line)
            if line.startswith("-"):
                hunk["removed"].append(line[1:])
            elif line.startswith("+"):
                hunk["added"].append(line[1:])
    close()
    return [unit for unit in units if unit.path and unit.path.endswith(".py")]
