# ABOUTME: Reads compost's pile.toml, the list of sources the plugin was made from, and reports upstream drift.
# ABOUTME: CLI: `status` maps upstream changes to compost skills, `advance` moves a pin, `notice` writes NOTICE.
import argparse
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PILE = PLUGIN_ROOT / "pile.toml"
CLONES = Path.home() / ".cache" / "compost" / "upstream"

ROLES = ("input", "frozen", "reference")


@dataclass(frozen=True)
class Source:
    name: str
    repo: str
    role: str
    license: str
    pin: str
    feeds: dict[str, list[str]] = field(default_factory=dict, hash=False)
    note: str = ""


@dataclass
class Drift:
    source: Source
    head: str
    by_skill: dict[str, list[str]]
    unmapped: list[str]


class PileError(Exception):
    pass


def load(path: Path = PILE) -> list[Source]:
    data = tomllib.loads(path.read_text())
    sources = [Source(**entry) for entry in data.get("source", [])]
    for source in sources:
        if source.role not in ROLES:
            raise PileError(f"{source.name}: role must be one of {', '.join(ROLES)}, not {source.role!r}")
    return sources


def map_changes(changed: list[str], feeds: dict[str, list[str]]) -> tuple[dict[str, list[str]], list[str]]:
    by_skill: dict[str, list[str]] = {}
    unmapped = []
    for path in changed:
        skills = sorted({skill for prefix, targets in feeds.items() if _under(path, prefix) for skill in targets})
        if not skills:
            unmapped.append(path)
        for skill in skills:
            by_skill.setdefault(skill, []).append(path)
    return by_skill, unmapped


def _under(path: str, prefix: str) -> bool:
    root = prefix.rstrip("/")
    return path == root or path.startswith(root + "/")


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise PileError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def clone_path(repo: str) -> Path:
    return CLONES / repo.replace("/", "_")


def git_compare(repo: str, pin: str) -> tuple[str, list[str]]:
    """Diffs a blobless clone, since GitHub's compare API stops listing files at 300."""
    path = clone_path(repo)
    if not (path / ".git").exists():
        url = f"https://github.com/{repo}.git"
        git("clone", "--quiet", "--filter=blob:none", "--no-checkout", url, str(path))
    else:
        git("-C", str(path), "fetch", "--quiet", "origin")
    head = git("-C", str(path), "rev-parse", "origin/HEAD").strip()
    changed = git("-C", str(path), "diff", "--name-only", pin, head).split()
    return head, sorted(changed)


def drift(sources: list[Source]) -> list[Drift]:
    report = []
    for source in sources:
        if source.role != "input":
            continue
        head, changed = git_compare(source.repo, source.pin)
        by_skill, unmapped = map_changes(changed, source.feeds)
        report.append(Drift(source, head, by_skill, unmapped))
    return report


def render_status(report: list[Drift]) -> str:
    lines = []
    for item in report:
        source = item.source
        if not item.by_skill and not item.unmapped:
            lines.append(f"{source.name} ({source.repo}): nothing new since {source.pin[:7]}")
            continue
        lines.append(f"{source.name} ({source.repo}): {source.pin[:7]} → {item.head}")
        lines.append(f"  diffs: git -C {clone_path(source.repo)} diff {source.pin} {item.head} -- <path>")
        for skill, paths in sorted(item.by_skill.items()):
            lines.append(f"  compost:{skill}")
            lines.extend(f"    {path}" for path in paths)
        if item.unmapped:
            lines.append(f"  {len(item.unmapped)} changed files feed no compost skill")
    return "\n".join(lines)


def advance(path: Path, name: str, commit: str) -> str:
    sources = {source.name: source for source in load(path)}
    if name not in sources:
        raise PileError(f"no source named {name!r} in {path.name}")
    old = f'pin = "{sources[name].pin}"'
    text = path.read_text()
    if text.count(old) != 1:
        raise PileError(f"{name}'s pin {sources[name].pin} is shared with another source; edit {path.name} by hand")
    path.write_text(text.replace(old, f'pin = "{commit}"'))
    return sources[name].pin


def render_notice(sources: list[Source]) -> str:
    lines = [
        "compost is made from other people's skills, reworked. Each source below keeps its license;",
        "their copyright notices apply to the parts of compost derived from them.",
        "",
    ]
    for source in sources:
        if source.role == "reference":
            continue
        lines.append(f"- {source.name}: https://github.com/{source.repo} ({source.license}), from {source.pin[:12]}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pile", description="Track the upstream sources compost was made from.")
    parser.add_argument("--pile", type=Path, default=PILE)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="list upstream changes since each input's pin, by compost skill")
    move = commands.add_parser("advance", help="move a source's pin once every change since it has a ruling")
    move.add_argument("source")
    move.add_argument("commit")
    notice = commands.add_parser("notice", help="write NOTICE from pile.toml")
    notice.add_argument("--check", action="store_true", help="exit 1 if NOTICE is out of date instead of writing")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            print(render_status(drift(load(args.pile))))
        elif args.command == "advance":
            old = advance(args.pile, args.source, args.commit)
            print(f"{args.source}: {old[:7]} → {args.commit[:7]}")
        else:
            notice_path = args.pile.parent / "NOTICE"
            expected = render_notice(load(args.pile))
            if args.check:
                if not notice_path.exists() or notice_path.read_text() != expected:
                    print(f"{notice_path} is out of date; run `pile.py notice`", file=sys.stderr)
                    return 1
            else:
                notice_path.write_text(expected)
    except PileError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
