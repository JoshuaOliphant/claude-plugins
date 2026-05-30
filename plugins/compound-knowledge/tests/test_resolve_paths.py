"""
ABOUTME: Tests for resolve_paths.py reservoir path resolution.
ABOUTME: Covers defaults, solutions_path back-compat, read/write split, precedence, vault_root.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import resolve_paths  # noqa: E402


def _write_cfg(dir_path: Path, body: str) -> None:
    cfg_dir = dir_path / ".claude"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "compound-knowledge.local.md").write_text(body, encoding="utf-8")


def test_default_when_no_config(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    result = resolve_paths.resolve(proj, home)
    expected = str(proj / "knowledge" / "solutions") + "/"
    assert result["write_path"] == expected
    assert result["read_paths"] == [expected]
    assert result["vault_root"] is None
    assert result["config_source"] == "default"


def test_solutions_path_back_compat(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "# Settings\nsolutions_path: /vault/knowledge/solutions/\n")
    result = resolve_paths.resolve(proj, home)
    assert result["write_path"] == "/vault/knowledge/solutions/"
    assert result["read_paths"] == ["/vault/knowledge/solutions/"]
    assert result["config_source"] == "project"


def test_read_write_split(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "write_path: /vault/knowledge/solutions/\nread_paths: /vault/wiki/, /vault/journal/\n")
    result = resolve_paths.resolve(proj, home)
    assert result["write_path"] == "/vault/knowledge/solutions/"
    assert result["read_paths"] == ["/vault/knowledge/solutions/", "/vault/wiki/", "/vault/journal/"]


def test_read_paths_dedup_write(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "write_path: /vault/knowledge/solutions/\nread_paths: /vault/knowledge/solutions/, /vault/wiki/\n")
    result = resolve_paths.resolve(proj, home)
    assert result["read_paths"] == ["/vault/knowledge/solutions/", "/vault/wiki/"]


def test_project_over_user_precedence(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(home, "solutions_path: /user/level/solutions/\n")
    _write_cfg(proj, "solutions_path: /project/level/solutions/\n")
    result = resolve_paths.resolve(proj, home)
    assert result["write_path"] == "/project/level/solutions/"
    assert result["config_source"] == "project"


def test_user_level_when_no_project_config(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(home, "solutions_path: /user/level/solutions/\n")
    result = resolve_paths.resolve(proj, home)
    assert result["write_path"] == "/user/level/solutions/"
    assert result["config_source"] == "user"


def test_vault_root_parsed(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "solutions_path: /vault/knowledge/solutions/\nvault_root: /vault\n")
    result = resolve_paths.resolve(proj, home)
    assert result["vault_root"] == "/vault/"
