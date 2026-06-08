"""Collect the working-tree diff as structured JSON."""

import re
import subprocess
from pathlib import Path
from typing import TypedDict


class NotAGitRepo(Exception):
    """Raised when the target path is not inside a git work tree."""


class GitCommandError(Exception):
    """Raised when a git command that must succeed exits non-zero.

    Carries the git stderr so callers can surface a real message instead of
    treating an empty stdout (a failed command) as "no changes".
    """

    def __init__(self, args, stderr):
        self.args = list(args)
        self.stderr = stderr.strip()
        super().__init__(f"git {' '.join(self.args)} failed: {self.stderr}")


def _run_git(args, cwd, check=False):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise GitCommandError(args, result.stderr)
    return result


def is_git_repo(path):
    result = _run_git(["rev-parse", "--is-inside-work-tree"], path)
    return result.returncode == 0 and result.stdout.strip() == "true"


def repo_name(path):
    result = _run_git(["rev-parse", "--show-toplevel"], path)
    top = result.stdout.strip()
    return Path(top).name if top else Path(path).name


class Line(TypedDict):
    side: str
    old_line: int | None
    new_line: int | None
    text: str


class Hunk(TypedDict):
    header: str
    lines: list[Line]


class FileDiff(TypedDict):
    path: str | None
    old_path: str | None
    status: str
    hunks: list[Hunk]


_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def get_untracked_files(path: str) -> list[str]:
    result = _run_git(["ls-files", "--others", "--exclude-standard"], path)
    return [line for line in result.stdout.splitlines() if line]


def build_untracked_file(rel_path: str, repo_root: str) -> FileDiff:
    full = Path(repo_root) / rel_path
    try:
        text = full.read_text(errors="replace")
    except OSError:
        text = ""
    lines = text.splitlines()
    hunks: list[Hunk] = []
    if lines:
        hunk_lines: list[Line] = [
            {"side": "new", "old_line": None, "new_line": i + 1, "text": ln}
            for i, ln in enumerate(lines)
        ]
        hunks = [{"header": f"@@ -0,0 +1,{len(lines)} @@", "lines": hunk_lines}]
    return {"path": rel_path, "old_path": None, "status": "untracked", "hunks": hunks}


_BASE_CANDIDATES = ("origin/main", "origin/master", "main", "master")


def resolve_base(path: str) -> str | None:
    """Return the first existing default-branch ref to diff a feature branch against."""
    for ref in _BASE_CANDIDATES:
        result = _run_git(["rev-parse", "--verify", "--quiet", ref], path)
        if result.returncode == 0:
            return ref
    return None


def collect_diff(path: str = ".", base: str | None = None) -> dict:
    if not is_git_repo(path):
        raise NotAGitRepo(path)
    if base is not None:
        # Branch-review mode: show what HEAD adds over its merge-base with `base`
        # (three-dot), matching what a GitLab/GitHub MR displays. Untracked files
        # are not part of the committed branch, so they are excluded here.
        diff_text = _run_git(["diff", "--no-prefix", f"{base}...HEAD"], path, check=True).stdout
        files = parse_unified_diff(diff_text)
    else:
        root = _run_git(["rev-parse", "--show-toplevel"], path).stdout.strip() or path
        diff_text = _run_git(["diff", "--no-prefix", "HEAD"], path, check=True).stdout
        files = parse_unified_diff(diff_text)
        for rel in get_untracked_files(path):
            files.append(build_untracked_file(rel, root))
    return {"repo": repo_name(path), "files": files, "has_changes": bool(files)}


def parse_unified_diff(diff_text: str) -> list[FileDiff]:
    """Parse `git diff` unified output into a list of file dicts."""
    files: list[FileDiff] = []
    current_file: FileDiff | None = None
    current_lines: list[Line] | None = None
    old_ln = new_ln = 0

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            current_file = {"path": None, "old_path": None, "status": "modified", "hunks": []}
            current_lines = None
            files.append(current_file)
        elif current_file is None:
            # Anything before the first "diff --git" header is preamble; skip it.
            continue
        elif line.startswith("--- "):
            old = line[4:]
            if old == "/dev/null":
                current_file["status"] = "added"
            else:
                current_file["old_path"] = old[2:] if old.startswith("a/") else old
        elif line.startswith("+++ "):
            new = line[4:]
            if new == "/dev/null":
                current_file["status"] = "deleted"
                current_file["path"] = current_file["old_path"]
            else:
                current_file["path"] = new[2:] if new.startswith("b/") else new
        elif line.startswith("Binary files "):
            # Binary files have no ---/+++/@@ lines, so derive the path here and
            # mark the status so the viewer can label it instead of rendering a
            # path-less "modified" entry. Format: "Binary files OLD and NEW differ".
            old_p, _, new_p = line[len("Binary files ") :].removesuffix(" differ").partition(" and ")
            current_file["status"] = "binary"
            current_file["path"] = new_p if new_p != "/dev/null" else old_p
            if old_p != "/dev/null":
                current_file["old_path"] = old_p
        elif line.startswith("@@"):
            match = _HUNK_RE.match(line)
            if match is None:
                continue
            old_ln = int(match.group(1))
            new_ln = int(match.group(2))
            current_lines = []
            current_file["hunks"].append({"header": line, "lines": current_lines})
        elif current_lines is not None:
            if line.startswith("+"):
                current_lines.append(
                    {"side": "new", "old_line": None, "new_line": new_ln, "text": line[1:]}
                )
                new_ln += 1
            elif line.startswith("-"):
                current_lines.append(
                    {"side": "old", "old_line": old_ln, "new_line": None, "text": line[1:]}
                )
                old_ln += 1
            elif line.startswith(" "):
                current_lines.append(
                    {"side": "context", "old_line": old_ln, "new_line": new_ln, "text": line[1:]}
                )
                old_ln += 1
                new_ln += 1
            # lines starting with "\" (e.g. "\ No newline at end of file") are ignored
    return files
