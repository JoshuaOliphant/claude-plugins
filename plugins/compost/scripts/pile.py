# ABOUTME: Reads compost's pile.toml: the sources compost was made from, and what it replaces on a machine.
# ABOUTME: CLI: `status`/`advance`/`notice` track upstream sources; `replaced` finds and turns off superseded skills.
import argparse
import dataclasses
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import MISSING, dataclass, field
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PILE = PLUGIN_ROOT / "pile.toml"
CLONES = Path.home() / ".cache" / "compost" / "upstream"
CLAUDE_DIR = Path.home() / ".claude"
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


@dataclass(frozen=True)
class Replaces:
    plugins: tuple[str, ...]
    skills: tuple[str, ...]


@dataclass
class Active:
    plugins: list[str]
    synced: list[str]
    skills: list[str]


def load_replaces(path: Path = PILE) -> Replaces:
    try:
        table = tomllib.loads(path.read_text()).get("replaces", {})
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise PileError(f"cannot read {path}: {error}") from error
    return Replaces(tuple(table.get("plugins", [])), tuple(table.get("skills", [])))


def find_active(replaces: Replaces, installed: list[dict], skill_names: set[str], overrides: dict) -> Active:
    enabled = {plugin["id"]: plugin.get("scope") for plugin in installed if plugin.get("enabled")}
    listed = [plugin_id for plugin_id in replaces.plugins if plugin_id in enabled]
    return Active(
        plugins=[plugin_id for plugin_id in listed if enabled[plugin_id] != "synced"],
        synced=[plugin_id for plugin_id in listed if enabled[plugin_id] == "synced"],
        skills=[name for name in replaces.skills if name in skill_names and overrides.get(name) != "off"],
    )


def claude(*args: str) -> str:
    try:
        result = subprocess.run(["claude", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError as error:
        raise PileError("the claude CLI is not on PATH") from error
    if result.returncode != 0:
        raise PileError(f"claude {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def installed_plugins() -> list[dict]:
    return json.loads(claude("plugin", "list", "--json"))


def personal_skills(claude_dir: Path) -> set[str]:
    skills = claude_dir / "skills"
    return {entry.name for entry in skills.iterdir()} if skills.is_dir() else set()


def read_settings(claude_dir: Path) -> dict:
    path = claude_dir / "settings.json"
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except json.JSONDecodeError as error:
        raise PileError(f"{path} is not valid JSON: {error}") from error


def turn_off_skills(claude_dir: Path, names: list[str]) -> None:
    settings = read_settings(claude_dir)
    overrides = settings.setdefault("skillOverrides", {})
    for name in names:
        overrides[name] = "off"
    path = claude_dir / "settings.json"
    with tempfile.NamedTemporaryFile("w", dir=claude_dir, delete=False, suffix=".tmp") as handle:
        handle.write(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
    os.replace(handle.name, path)


def render_active(active: Active) -> str:
    if not (active.plugins or active.synced or active.skills):
        return "Nothing compost replaces is active here."
    lines = ["compost replaces these, and they are still active here:"]
    if active.plugins:
        lines.append(f"  plugins to disable: {', '.join(active.plugins)}")
    if active.skills:
        lines.append(f"  skills to set off in skillOverrides: {', '.join(active.skills)}")
    if active.synced:
        lines.append(f"  synced from claude.ai, turn off in your claude.ai settings: {', '.join(active.synced)}")
    return "\n".join(lines)


def replaced(pile: Path, claude_dir: Path, apply: bool) -> str:
    replaces = load_replaces(pile)
    overrides = read_settings(claude_dir).get("skillOverrides", {})
    active = find_active(replaces, installed_plugins(), personal_skills(claude_dir), overrides)
    report = render_active(active)
    if not apply or not (active.plugins or active.skills):
        return report
    for plugin_id in active.plugins:
        claude("plugin", "disable", plugin_id, "--json")
    if active.skills:
        turn_off_skills(claude_dir, active.skills)
    done = [f"disabled {len(active.plugins)} plugins", f"set {len(active.skills)} skills off in skillOverrides"]
    remaining = f"; still to do by hand: {', '.join(active.synced)} on claude.ai" if active.synced else ""
    return f"{report}\n{'; '.join(done)}{remaining}. Restart Claude Code to apply."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pile", description="Track the upstream sources compost was made from.")
    parser.add_argument("--pile", type=Path, default=PILE)
    commands = parser.add_subparsers(dest="command", required=True)
    superseded = commands.add_parser("replaced", help="list what compost replaces that is still active on this machine")
    superseded.add_argument("--apply", action="store_true", help="disable those plugins and set those skills off")
    superseded.add_argument("--claude-dir", type=Path, default=CLAUDE_DIR)
    commands.add_parser("status", help="list upstream changes since each input's pin, by compost skill")
    move = commands.add_parser("advance", help="move SOURCE's pin to COMMIT, resolved to a full hash upstream")
    move.add_argument("source")
    move.add_argument("commit")
    notice = commands.add_parser("notice", help="write NOTICE from pile.toml")
    notice.add_argument("--check", action="store_true", help="exit 1 if NOTICE is out of date instead of writing")
    args = parser.parse_args(argv)
    try:
        if args.command == "replaced":
            print(replaced(args.pile, args.claude_dir, args.apply))
        elif args.command == "status":
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
