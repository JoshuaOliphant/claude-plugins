"""
ABOUTME: Tests for resolve_config.py understand-plugin settings resolution.
ABOUTME: Covers defaults, overrides, bool/int parsing, precedence, tilde expansion.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import resolve_config  # noqa: E402


def _write_cfg(dir_path: Path, body: str) -> None:
    cfg_dir = dir_path / ".claude"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "understand.local.md").write_text(body, encoding="utf-8")


def test_defaults_when_no_config(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    result = resolve_config.resolve(proj, home)
    assert result["mochi_deck"] == ""
    assert result["session_dir"] == str(proj / "understand-sessions") + "/"
    assert result["follow_references"] is True
    assert result["strictness"] == "struggle-then-teach"
    assert result["card_cap"] == 10
    assert result["config_source"] == "default"


def test_full_override(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, (
        "mochi_deck: Learning\n"
        "session_dir: /vault/areas/learning/sessions/\n"
        "follow_references: false\n"
        "strictness: pure-examiner\n"
        "card_cap: 5\n"
    ))
    result = resolve_config.resolve(proj, home)
    assert result["mochi_deck"] == "Learning"
    assert result["session_dir"] == "/vault/areas/learning/sessions/"
    assert result["follow_references"] is False
    assert result["strictness"] == "pure-examiner"
    assert result["card_cap"] == 5
    assert result["config_source"] == "project"


def test_invalid_card_cap_falls_back_to_default(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "card_cap: lots\n")
    result = resolve_config.resolve(proj, home)
    assert result["card_cap"] == 10


def test_follow_references_bool_parsing(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "follow_references: YES\n")
    result = resolve_config.resolve(proj, home)
    assert result["follow_references"] is True


def test_project_over_user_precedence(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(home, "mochi_deck: UserDeck\n")
    _write_cfg(proj, "mochi_deck: ProjectDeck\n")
    result = resolve_config.resolve(proj, home)
    assert result["mochi_deck"] == "ProjectDeck"
    assert result["config_source"] == "project"


def test_session_dir_tilde_expanded(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "session_dir: ~/vault/sessions/\n")
    result = resolve_config.resolve(proj, home)
    assert not result["session_dir"].startswith("~")
    assert result["session_dir"].endswith("/")


def test_relative_session_dir_anchored_to_project(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(proj, "session_dir: my-sessions/\n")
    result = resolve_config.resolve(proj, home)
    assert result["session_dir"] == str(proj / "my-sessions") + "/"


def test_user_only_config(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    proj = tmp_path / "proj"; proj.mkdir()
    _write_cfg(home, "mochi_deck: UserDeck\n")
    result = resolve_config.resolve(proj, home)
    assert result["mochi_deck"] == "UserDeck"
    assert result["config_source"] == "user"
