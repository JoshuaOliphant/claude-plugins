# ABOUTME: Reads this machine's Claude Code config: plugins as the `claude` CLI lists them, personal skills, settings.json.
# ABOUTME: Owns the one policy for whether a plugin or skill is active here; skill_drift and `pile.py replaced` share it.
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"


class ClaudeConfigError(Exception):
    pass


def claude(*args: str) -> str:
    try:
        result = subprocess.run(["claude", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError as error:
        raise ClaudeConfigError("the claude CLI is not on PATH") from error
    if result.returncode != 0:
        raise ClaudeConfigError(f"claude {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
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
        raise ClaudeConfigError(f"{path} is not valid JSON: {error}") from error


def turn_off_skills(claude_dir: Path, names: list[str]) -> None:
    settings = read_settings(claude_dir)
    overrides = settings.setdefault("skillOverrides", {})
    for name in names:
        overrides[name] = "off"
    path = claude_dir / "settings.json"
    with tempfile.NamedTemporaryFile("w", dir=claude_dir, delete=False, suffix=".tmp") as handle:
        handle.write(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
    os.replace(handle.name, path)


@dataclass(frozen=True)
class Config:
    """Enabled plugins come from `claude plugin list --json`: the CLI merges every settings scope and the plugins
    synced from claude.ai, which `enabledPlugins` in ~/.claude/settings.json alone does not. `synced` holds the
    enabled ones only claude.ai can turn off. Skills are switched off only by `skillOverrides` in settings.json."""

    enabled: frozenset[str]
    synced: frozenset[str]
    personal: frozenset[str]
    overrides: dict[str, str]

    def plugin_enabled(self, plugin_id: str) -> bool:
        """`plugin_id` is `plugin@marketplace`."""
        return plugin_id in self.enabled

    def is_synced(self, plugin_id: str) -> bool:
        return plugin_id in self.synced

    def skill_active(self, name: str) -> bool:
        """`name` is a plugin's skill (`plugin:skill`), active under any marketplace's `plugin`, or a personal skill."""
        if self.overrides.get(name) == "off":
            return False
        if ":" not in name:
            return name in self.personal
        plugin = name.split(":", 1)[0]
        return any(plugin_id.split("@", 1)[0] == plugin for plugin_id in self.enabled)


def read(claude_dir: Path) -> Config:
    overrides = read_settings(claude_dir).get("skillOverrides", {})
    enabled = [plugin for plugin in installed_plugins() if plugin.get("enabled")]
    return Config(
        enabled=frozenset(plugin["id"] for plugin in enabled),
        synced=frozenset(plugin["id"] for plugin in enabled if plugin.get("scope") == "synced"),
        personal=frozenset(personal_skills(claude_dir)),
        overrides=overrides,
    )
