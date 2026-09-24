# ABOUTME: Reads compost's pile.toml, the list of sources the plugin was made from, and reports upstream drift.
# ABOUTME: CLI: `status` maps upstream changes to compost skills, `advance` moves a pin, `notice` writes NOTICE.
import argparse
import dataclasses
import subprocess
import sys
import tomllib
from dataclasses import MISSING, dataclass, field
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PILE = PLUGIN_ROOT / "pile.toml"
CLONES = Path.home() / ".cache" / "compost" / "upstream"
UNMAPPED_SHOWN = 20

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
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise PileError(f"cannot read {path}: {error}") from error
    fields = {f.name for f in dataclasses.fields(Source)}
    required = {f.name for f in dataclasses.fields(Source) if f.default is MISSING and f.default_factory is MISSING}
    sources = []
    for index, entry in enumerate(data.get("source", [])):
        label = f"source {index + 1} ({entry.get('name', 'unnamed')})"
        if missing := sorted(required - entry.keys()):
            raise PileError(f"{label}: missing {', '.join(missing)}")
        if unknown := sorted(entry.keys() - fields):
            raise PileError(f"{label}: unknown field {', '.join(unknown)}")
        if entry["role"] not in ROLES:
            raise PileError(f"{entry['name']}: role must be one of {', '.join(ROLES)}, not {entry['role']!r}")
        sources.append(Source(**entry))
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
    try:
        result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError as error:
        raise PileError("git not found on PATH") from error
    if result.returncode != 0:
        raise PileError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def clone_path(repo: str) -> Path:
    return CLONES / repo.replace("/", "_")


def sync_clone(repo: str) -> Path:
    """Keeps a blobless clone, since GitHub's compare API stops listing files at 300."""
    path = clone_path(repo)
    if not (path / ".git").exists():
        url = f"https://github.com/{repo}.git"
        git("clone", "--quiet", "--filter=blob:none", "--no-checkout", url, str(path))
    else:
        git("-C", str(path), "fetch", "--quiet", "--prune", "origin")
        git("-C", str(path), "remote", "set-head", "origin", "--auto")
    return path


def git_compare(repo: str, pin: str) -> tuple[str, list[str]]:
    path = sync_clone(repo)
    head = git("-C", str(path), "rev-parse", "origin/HEAD").strip()
    output = git("-C", str(path), "diff", "--name-only", "--no-renames", "-z", pin, head)
    return head, sorted(name for name in output.split("\0") if name)


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
            lines.append("  feed no compost skill:")
            lines.extend(f"    {path}" for path in item.unmapped[:UNMAPPED_SHOWN])
            if len(item.unmapped) > UNMAPPED_SHOWN:
                lines.append(f"    and {len(item.unmapped) - UNMAPPED_SHOWN} more")
    return "\n".join(lines)


def advance(path: Path, name: str, commit: str) -> tuple[str, str]:
    sources = {source.name: source for source in load(path)}
    if name not in sources:
        raise PileError(f"no source named {name!r} in {path.name}")
    source = sources[name]
    old = f'pin = "{source.pin}"'
    text = path.read_text()
    if text.count(old) == 0:
        raise PileError(f"{name}'s pin is not written as `{old}` in {path.name}; edit it by hand")
    if text.count(old) > 1:
        raise PileError(f"{name}'s pin {source.pin} is shared with another source; edit {path.name} by hand")
    clone = sync_clone(source.repo)
    try:
        resolved = git("-C", str(clone), "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}").strip()
    except PileError as error:
        raise PileError(f"{commit} is not a commit in {source.repo}") from error
    path.write_text(text.replace(old, f'pin = "{resolved}"'))
    return source.pin, resolved


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
    move = commands.add_parser("advance", help="move SOURCE's pin to COMMIT, resolved to a full hash upstream")
    move.add_argument("source")
    move.add_argument("commit")
    notice = commands.add_parser("notice", help="write NOTICE from pile.toml")
    notice.add_argument("--check", action="store_true", help="exit 1 if NOTICE is out of date instead of writing")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            print(render_status(drift(load(args.pile))))
        elif args.command == "advance":
            old, new = advance(args.pile, args.source, args.commit)
            print(f"{args.source}: {old[:7]} → {new[:7]}")
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
