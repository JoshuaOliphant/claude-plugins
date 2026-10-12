# ABOUTME: Finds doc drift candidates for compost:prune: in every tracked markdown file, the file references that no
# ABOUTME: longer resolve, and the referenced files that changed since the doc last did. Stdlib only; reads git.
import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

# Docs that hold what code can't say. Matched from the right, like PurePosixPath.match, so they apply at any depth.
CORE = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "CONTEXT.md",
    "CONTEXT-MAP.md",
    "CHANGELOG.md",
    "docs/adr/*.md",
    "docs/agents/*.md",
)
EXTENSIONS = {
    "cfg", "css", "go", "html", "ini", "js", "json", "jsx", "lock", "md", "mjs", "py", "rb", "rs", "sh", "sql",
    "toml", "ts", "tsx", "txt", "yaml", "yml",
}  # fmt: skip
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
CODE = re.compile(r"`([^`\s]+)`")
NOT_A_PATH = re.compile(r"[*<>{}$|:@~=]|^[-/]")


class DocRefsError(Exception):
    pass


@dataclass
class Doc:
    path: str
    core: bool
    refs: int = 0
    missing: list[str] = field(default_factory=list)
    stale: dict[str, int] = field(default_factory=dict)


def path_refs(text: str) -> list[str]:
    """Relative links, and inline code that looks like a file path, in order of first appearance."""
    found = [target for target in LINK.findall(text) if "://" not in target and not target.startswith("mailto:")]
    for token in CODE.findall(text):
        if NOT_A_PATH.search(token) or "://" in token:
            continue
        suffix = PurePosixPath(token.rstrip("/")).suffix.lstrip(".")
        if "/" in token or suffix in EXTENSIONS:
            found.append(token)
    return list(dict.fromkeys(ref.removeprefix("./") for ref in found))


def resolve(ref: str, doc: PurePosixPath, root: Path, tracked: list[str]) -> str | None:
    """The repo-relative path a reference means, trying the doc's directory, then each directory above it.

    A bare file name resolves to the one tracked file of that name. When several share it, the result is "": present,
    but too ambiguous to check for staleness. None means nothing matches.
    """
    for base in [doc.parent, *doc.parent.parents]:
        candidate = (root / base / ref).resolve()
        if candidate.exists() and candidate.is_relative_to(root):
            return candidate.relative_to(root).as_posix()
    if "/" not in ref.rstrip("/"):
        matches = [name for name in tracked if PurePosixPath(name).name == ref]
        if len(matches) == 1:
            return matches[0]
        if matches:
            return ""
    return None


def scan(root: Path, core: tuple[str, ...] = CORE, exclude: tuple[str, ...] = ()) -> list[Doc]:
    root = root.resolve()
    docs = []
    tracked = list(filter(None, _git(root, "ls-files", "-z").split("\0")))
    for name in [name for name in tracked if name.endswith(".md")]:
        path = PurePosixPath(name)
        if not (root / name).is_file() or any(path.match(pattern) for pattern in exclude):
            continue
        doc = Doc(name, any(path.match(pattern) for pattern in core))
        refs = path_refs((root / name).read_text(errors="replace"))
        doc.refs = len(refs)
        last = _git(root, "log", "-1", "--format=%H", "--", name).strip()
        for ref in refs:
            target = resolve(ref, path, root, tracked)
            if target is None:
                doc.missing.append(ref)
            elif last and target and target != name and (commits := _commits_since(root, last, target)):
                doc.stale[target] = commits
        docs.append(doc)
    return sorted(docs, key=lambda d: (d.core, -len(d.missing), -sum(d.stale.values()), d.path))


def _commits_since(root: Path, commit: str, path: str) -> int:
    return int(_git(root, "rev-list", "--count", f"{commit}..HEAD", "--", path))


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise DocRefsError(f"git {args[0]} failed in {root}: {result.stderr.strip()}")
    return result.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find doc drift candidates for compost:prune.")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("scan", help="list every tracked markdown doc with its missing and stale references")
    run.add_argument("--root", type=Path, default=Path.cwd())
    run.add_argument("--core", action="append", default=[], help="another core doc pattern (repeatable)")
    run.add_argument("--exclude", action="append", default=[], help="a doc pattern to leave out (repeatable)")
    args = parser.parse_args(argv)
    try:
        docs = scan(args.root, CORE + tuple(args.core), tuple(args.exclude))
    except DocRefsError as error:
        print(error, file=sys.stderr)
        return 2
    print(json.dumps([asdict(doc) for doc in docs], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
