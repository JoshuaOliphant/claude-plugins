# ABOUTME: Turns Python source and unified diffs into lintable units: comments, except handlers, functions, log calls, hunks.
# ABOUTME: Pure stdlib (ast, tokenize); each unit carries the state Jev needs to judge it.

import ast
import io
import re
import tokenize
from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["comment", "handler", "function", "log_call", "hunk"]

STATE_KEYS: dict[str, set[str]] = {
    "comment": {"comment", "code_before", "code_after", "inline_code"},
    "handler": {"try_statement", "handler"},
    "function": {"qualified_name", "function", "docstring"},
    "log_call": {"log_call", "enclosing_function"},
    "hunk": {"path", "hunk", "removed", "added"},
}

CONTEXT_LINES = 3
MAX_SEGMENT_LINES = 80

DIRECTIVE = re.compile(
    r"^#(!|\s*(ABOUTME:|-\*-|noqa|type:|pragma|pyright:|ruff:|fmt:|mypy:|isort:|pylint:))"
)
SCRIPT_BLOCK_START = "# /// script"
SCRIPT_BLOCK_END = "# ///"
BROAD_EXCEPTIONS = {"Exception", "BaseException"}
LOG_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "log"}
LOGGER_NAMES = {"log", "logger", "logging"}
LOGGER_SUFFIXES = ("_log", "_logger")
NO_NEWLINE_MARKER = "\\ "


@dataclass(frozen=True)
class Unit:
    kind: Kind
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


def _script_block_rows(tokens: list[tokenize.TokenInfo]) -> set[int]:
    rows: set[int] = set()
    start = None
    for token in tokens:
        text = token.string.strip()
        if start is None and text == SCRIPT_BLOCK_START:
            start = token.start[0]
        elif start is not None and text == SCRIPT_BLOCK_END:
            rows.update(range(start, token.start[0] + 1))
            start = None
    return rows


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
    tokens = _comment_tokens(source)
    script_rows = _script_block_rows(tokens)
    blocks: list[list[tokenize.TokenInfo]] = []
    for token in tokens:
        row, col = token.start
        if row in script_rows or DIRECTIVE.match(token.string.strip()):
            continue
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
        inline_code = lines[first - 1][: block[0].start[1]].rstrip()
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


def _called_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _is_logger(node: ast.expr) -> bool:
    if isinstance(node, ast.Call):
        return _called_name(node.func) == "getLogger"
    name = _called_name(node).lower()
    return name in LOGGER_NAMES or name.endswith(LOGGER_SUFFIXES)


def _exception_names(node: ast.expr | None) -> list[str]:
    if node is None:
        return []
    elements = node.elts if isinstance(node, ast.Tuple) else [node]
    return [ast.unparse(element) for element in elements]


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
            exceptions = _exception_names(handler.type)
            name = ast.unparse(handler.type) if handler.type else "bare except"
            facts = {
                "bare": handler.type is None,
                "broad": any(exception in BROAD_EXCEPTIONS for exception in exceptions),
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


HUNK_HEADER = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def extract_hunks(diff: str) -> list[Unit]:
    units = []
    old_path = path = None
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
        if hunk and (hunk["old_left"] > 0 or hunk["new_left"] > 0):
            if line.startswith(NO_NEWLINE_MARKER):
                continue
            hunk["lines"].append(line)
            if line.startswith("-"):
                hunk["removed"].append(line[1:])
                hunk["old_left"] -= 1
            elif line.startswith("+"):
                hunk["added"].append(line[1:])
                hunk["new_left"] -= 1
            else:
                hunk["old_left"] -= 1
                hunk["new_left"] -= 1
        elif line.startswith("--- "):
            old_path = line[4:].removeprefix("a/")
        elif line.startswith("+++ "):
            close()
            hunk = None
            target = line[4:]
            path = old_path if target == "/dev/null" else target.removeprefix("b/")
        elif line.startswith("@@"):
            close()
            match = HUNK_HEADER.match(line)
            hunk = match and {
                "start": int(match.group(2)),
                "old_left": int(match.group(1) or 1),
                "new_left": int(match.group(3) or 1),
                "lines": [],
                "removed": [],
                "added": [],
            }
    close()
    return [unit for unit in units if unit.path and unit.path.endswith(".py")]
