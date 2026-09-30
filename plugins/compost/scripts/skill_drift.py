# ABOUTME: Reads the skill-drift log (~/.claude/skill-drift/*.jsonl): hits where Jev judged a turn drifted from a skill.
# ABOUTME: CLI: `patterns` groups unreviewed hits on active skills into cross-session patterns; `mark` records reviews.
import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pile

MIN_SESSIONS = 2
REVIEWED = "reviewed.json"


@dataclass(frozen=True)
class Hit:
    skill: str
    kind: str
    p: float
    at: int
    session: str
    turn: str
    skill_hash: str
    prompt: str
    evidence: str

    @property
    def id(self) -> str:
        return f"{self.session}:{self.turn}:{self.skill}:{self.kind}"


@dataclass
class Pattern:
    skill: str
    kind: str
    owner: str
    file: str | None
    sessions: int
    earlier_versions: int
    hits: list[dict] = field(default_factory=list)


@dataclass
class Log:
    hits: list[Hit]
    unreadable: int


def log_dir(claude_dir: Path) -> Path:
    return claude_dir / "skill-drift"


def read_log(claude_dir: Path) -> Log:
    hits, unreadable = [], 0
    for path in sorted(log_dir(claude_dir).glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                hits.append(Hit(**json.loads(line)))
            except (json.JSONDecodeError, TypeError):
                unreadable += 1
    return Log(hits, unreadable)


def reviewed(claude_dir: Path) -> set[str]:
    path = log_dir(claude_dir) / REVIEWED
    return set(json.loads(path.read_text())) if path.exists() else set()


def mark(claude_dir: Path, ids: list[str]) -> int:
    done = reviewed(claude_dir) | set(ids)
    path = log_dir(claude_dir) / REVIEWED
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(done), indent=2) + "\n")
    return len(done)


def is_active(skill: str, settings: dict, personal: set[str]) -> bool:
    if settings.get("skillOverrides", {}).get(skill) == "off":
        return False
    if ":" not in skill:
        return skill in personal
    plugin = skill.split(":", 1)[0]
    return any(key.split("@", 1)[0] == plugin and on for key, on in settings.get("enabledPlugins", {}).items())


def owner(skill: str, claude_dir: Path, repo: Path) -> tuple[str, str | None]:
    if ":" not in skill:
        return "personal", str((claude_dir / "skills" / skill / "SKILL.md").resolve())
    plugin, name = skill.split(":", 1)
    in_repo = repo / "plugins" / plugin / "skills" / name / "SKILL.md"
    return ("repo", str(in_repo.relative_to(repo))) if in_repo.exists() else ("third-party", None)


def transcript(claude_dir: Path, session: str) -> str | None:
    found = sorted((claude_dir / "projects").glob(f"*/{session}.jsonl"))
    return str(found[0]) if found else None


@dataclass
class Group:
    skill: str
    kind: str
    hits: list[Hit]
    earlier_versions: int


def group_hits(hits: list[Hit], active: set[str], done: set[str], min_sessions: int) -> tuple[list[Group], dict]:
    retired: dict[str, int] = defaultdict(int)
    latest: dict[str, Hit] = {}
    for hit in hits:
        if hit.skill not in active:
            retired[hit.skill] += 1
        elif hit.skill not in latest or hit.at > latest[hit.skill].at:
            latest[hit.skill] = hit

    current: dict[tuple[str, str], list[Hit]] = defaultdict(list)
    earlier: dict[tuple[str, str], int] = defaultdict(int)
    for hit in hits:
        if hit.skill not in latest:
            continue
        key = (hit.skill, hit.kind)
        if hit.skill_hash != latest[hit.skill].skill_hash:
            earlier[key] += 1
        elif hit.id not in done:
            current[key].append(hit)

    groups = [
        Group(skill, kind, grouped, earlier[(skill, kind)])
        for (skill, kind), grouped in sorted(current.items())
        if len({hit.session for hit in grouped}) >= min_sessions
    ]
    return groups, dict(retired)


def patterns(claude_dir: Path, repo: Path, min_sessions: int = MIN_SESSIONS) -> dict:
    log = read_log(claude_dir)
    settings = pile.read_settings(claude_dir)
    personal = pile.personal_skills(claude_dir)
    active = {hit.skill for hit in log.hits if is_active(hit.skill, settings, personal)}
    groups, retired = group_hits(log.hits, active, reviewed(claude_dir), min_sessions)
    found = []
    for group in groups:
        who, file = owner(group.skill, claude_dir, repo)
        found.append(
            Pattern(
                skill=group.skill,
                kind=group.kind,
                owner=who,
                file=file,
                sessions=len({hit.session for hit in group.hits}),
                earlier_versions=group.earlier_versions,
                hits=[
                    {**asdict(hit), "id": hit.id, "transcript": transcript(claude_dir, hit.session)}
                    for hit in group.hits
                ],
            )
        )
    return {"patterns": [asdict(pattern) for pattern in found], "retired": retired, "unreadable": log.unreadable}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skill_drift", description="Review the skill-drift log.")
    parser.add_argument("--claude-dir", type=Path, default=pile.CLAUDE_DIR)
    commands = parser.add_subparsers(dest="command", required=True)
    grouped = commands.add_parser("patterns", help="print unreviewed cross-session patterns on active skills as JSON")
    grouped.add_argument("--min-sessions", type=int, default=MIN_SESSIONS)
    grouped.add_argument("--repo", type=Path, default=Path.cwd(), help="the marketplace checkout; default the cwd")
    marking = commands.add_parser("mark", help="record hits as reviewed so later runs leave them out")
    marking.add_argument("ids", nargs="+")
    args = parser.parse_args(argv)
    try:
        if args.command == "patterns":
            print(json.dumps(patterns(args.claude_dir, args.repo, args.min_sessions), indent=2))
        else:
            print(f"{mark(args.claude_dir, args.ids)} hits reviewed in all")
    except pile.PileError as error:
        print(f"skill_drift: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
