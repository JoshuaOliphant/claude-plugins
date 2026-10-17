# ABOUTME: Reads this machine's Claude Code config: plugins and marketplace catalogs via the `claude` CLI, personal
# ABOUTME: skills, settings.json.
# ABOUTME: Owns the policy for whether a plugin or skill is active here, shared by skill_drift and `pile.py replaced`.
import json
import os
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
UNINSTALLABLE_SCOPES = frozenset({"user", "project", "local"})


class ClaudeConfigError(Exception):
    pass


def claude(*args: str, claude_dir: Path | None = None) -> str:
    """Runs the CLI against `claude_dir` through CLAUDE_CONFIG_DIR when it is not the default ~/.claude."""
    env = None
    if claude_dir is not None and claude_dir != CLAUDE_DIR:
        env = os.environ | {"CLAUDE_CONFIG_DIR": str(claude_dir)}
    try:
        result = subprocess.run(["claude", *args], capture_output=True, text=True, check=False, env=env)
    except FileNotFoundError as error:
        raise ClaudeConfigError("the claude CLI is not on PATH") from error
    if result.returncode != 0:
        raise ClaudeConfigError(f"claude {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def _claude_json(*args: str, claude_dir: Path | None) -> list[dict]:
    output = claude(*args, "--json", claude_dir=claude_dir)
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise ClaudeConfigError(f"claude {' '.join(args)} --json printed no JSON: {error}") from error


def installed_plugins(claude_dir: Path | None = None) -> list[dict]:
    return _claude_json("plugin", "list", claude_dir=claude_dir)


def marketplace_listings(claude_dir: Path | None = None) -> dict[str, frozenset[str]]:
    """Each configured marketplace, mapped to the plugin names its local clone's catalog lists. A marketplace whose
    clone has no catalog is left out: nothing can be said about what it lists."""
    listings = {}
    for marketplace in _claude_json("plugin", "marketplace", "list", claude_dir=claude_dir):
        catalog = Path(marketplace["installLocation"]) / ".claude-plugin" / "marketplace.json"
        if not catalog.is_file():
            continue
        try:
            plugins = json.loads(catalog.read_text()).get("plugins", [])
        except json.JSONDecodeError as error:
            raise ClaudeConfigError(f"{catalog} is not valid JSON: {error}") from error
        listings[marketplace["name"]] = frozenset(plugin["name"] for plugin in plugins)
    return listings


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


@dataclass
class Config:
    """Enabled plugins come from `claude plugin list --json`, run only when a plugin or plugin skill is asked about:
    the CLI merges every settings scope and the plugins synced from claude.ai, which `enabledPlugins` in
    settings.json alone does not. Skills are switched off only by `skillOverrides` in settings.json."""

    personal: frozenset[str]
    overrides: dict[str, str]
    list_plugins: Callable[[], list[dict]]
    list_marketplaces: Callable[[], dict[str, frozenset[str]]] = dict

    @cached_property
    def _listing(self) -> list[dict]:
        return self.list_plugins()

    @cached_property
    def enabled(self) -> frozenset[str]:
        return frozenset(plugin["id"] for plugin in self._listing if plugin.get("enabled"))

    @cached_property
    def synced(self) -> frozenset[str]:
        """Enabled ids only claude.ai can turn off: synced, with no enabled install at a local scope."""
        scopes: dict[str, set] = {}
        for plugin in self._listing:
            if plugin.get("enabled"):
                scopes.setdefault(plugin["id"], set()).add(plugin.get("scope"))
        return frozenset(plugin_id for plugin_id, found in scopes.items() if found == {"synced"})

    @cached_property
    def orphaned(self) -> list[tuple[str, str]]:
        """Installs, enabled or not, as `(plugin@marketplace, scope)`, that their marketplace's clone no longer lists.
        Installs from a marketplace with no clone (claude.ai's synced plugins, a removed marketplace) prove nothing,
        and a scope the CLI cannot uninstall from is not offered."""
        listings = self.list_marketplaces()
        orphans = []
        for plugin in self._listing:
            name, _, marketplace = plugin["id"].partition("@")
            scope = plugin.get("scope")
            if marketplace in listings and name not in listings[marketplace] and scope in UNINSTALLABLE_SCOPES:
                orphans.append((plugin["id"], scope))
        return orphans

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
    return Config(
        personal=frozenset(personal_skills(claude_dir)),
        overrides=read_settings(claude_dir).get("skillOverrides", {}),
        list_plugins=lambda: installed_plugins(claude_dir),
        list_marketplaces=lambda: marketplace_listings(claude_dir),
    )
