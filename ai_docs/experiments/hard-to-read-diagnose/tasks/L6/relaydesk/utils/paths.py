"""Locating the project root and well-known files inside it."""

from __future__ import annotations

from pathlib import Path

MARKER = Path("config") / "relaydesk.toml"
PACKAGE_DIR = Path(__file__).resolve().parent.parent


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from *start* (default: cwd) to the first directory holding
    ``config/relaydesk.toml``.  Falls back to the directory containing the
    package so ``python -m relaydesk`` works from anywhere in a checkout."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / MARKER).is_file():
            return candidate
    return PACKAGE_DIR.parent


def env_files(root: Path) -> list[Path]:
    """Dotenv files consulted at start-up, lowest precedence first."""
    return [root / ".env", root / ".env.local"]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)
