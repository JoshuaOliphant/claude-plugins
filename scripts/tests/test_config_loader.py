"""
ABOUTME: Tests for the canonical shared config_loader: project>user>default precedence and directory().
ABOUTME: The per-plugin copies are byte-identical (sync_shared.py), so these cover every consumer.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
import config_loader  # noqa: E402

CONFIG_NAME = "demo.local.md"


def _write_cfg(dir_path: Path, body: str) -> None:
    cfg_dir = dir_path / ".claude"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / CONFIG_NAME).write_text(body, encoding="utf-8")


@pytest.fixture
def roots(tmp_path):
    home = tmp_path / "home"
    proj = tmp_path / "proj"
    home.mkdir()
    proj.mkdir()
    return proj, home


@pytest.mark.parametrize(
    "project_body, user_body, expected",
    [
        pytest.param(
            "key: project\n", "key: user\n", ({"key": "project"}, "project"), id="project-wins"
        ),
        pytest.param(None, "key: user\n", ({"key": "user"}, "user"), id="user-when-no-project"),
        pytest.param(None, None, ({}, "default"), id="default-when-neither"),
        # A project file shadows the user file wholesale; keys are not merged across levels.
        pytest.param(
            "other: x\n", "key: user\n", ({"other": "x"}, "project"), id="no-merge-across-levels"
        ),
    ],
)
def test_find_config_precedence(roots, project_body, user_body, expected):
    proj, home = roots
    if project_body is not None:
        _write_cfg(proj, project_body)
    if user_body is not None:
        _write_cfg(home, user_body)
    assert config_loader.find_config(proj, home, CONFIG_NAME) == expected


def test_parse_config_keeps_only_key_value_lines(tmp_path):
    cfg = tmp_path / CONFIG_NAME
    cfg.write_text(
        "# Settings\n\nwrite_path:  /a/b/ \nNot A Key: x\nprose line\n", encoding="utf-8"
    )
    assert config_loader.parse_config(cfg) == {"write_path": "/a/b/"}


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param("/abs/dir", "/abs/dir/", id="absolute-gets-trailing-slash"),
        pytest.param("/abs/dir///", "/abs/dir/", id="trailing-slashes-collapse"),
        pytest.param("rel/dir/", "{proj}/rel/dir/", id="relative-anchors-to-project-root"),
        pytest.param("~/notes", "{home}/notes/", id="tilde-expands"),
    ],
)
def test_directory_normalizes_against_project_root(roots, monkeypatch, value, expected):
    proj, home = roots
    monkeypatch.setenv("HOME", str(home))
    # The working directory is not the base: a relative value must not land under it.
    monkeypatch.chdir(home)
    assert config_loader.directory(value, proj) == expected.format(proj=proj, home=home)
