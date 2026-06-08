import subprocess

import pytest

from collect import (
    NotAGitRepo,
    build_untracked_file,
    collect_diff,
    get_untracked_files,
    is_git_repo,
    parse_unified_diff,
    repo_name,
)


def _init_repo(path):
    for args in (
        ["git", "init"],
        ["git", "config", "user.email", "t@example.com"],
        ["git", "config", "user.name", "Tester"],
    ):
        subprocess.run(args, cwd=path, check=True, capture_output=True)


def test_is_git_repo_true(tmp_path):
    _init_repo(tmp_path)
    assert is_git_repo(str(tmp_path)) is True


def test_is_git_repo_false(tmp_path):
    assert is_git_repo(str(tmp_path)) is False


def test_repo_name(tmp_path):
    _init_repo(tmp_path)
    assert repo_name(str(tmp_path)) == tmp_path.name


MODIFIED_DIFF = """diff --git a/foo.py b/foo.py
index 1234567..89abcde 100644
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,3 @@
 unchanged
-old line
+new line
 trailing
"""

ADDED_DIFF = """diff --git a/new.py b/new.py
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/new.py
@@ -0,0 +1,2 @@
+first
+second
"""

DELETED_DIFF = """diff --git a/gone.py b/gone.py
deleted file mode 100644
index 1111111..0000000
--- a/gone.py
+++ /dev/null
@@ -1,1 +0,0 @@
-was here
"""


def test_parse_modified():
    files = parse_unified_diff(MODIFIED_DIFF)
    assert len(files) == 1
    f = files[0]
    assert f["path"] == "foo.py"
    assert f["status"] == "modified"
    lines = f["hunks"][0]["lines"]
    assert [ln["side"] for ln in lines] == ["context", "old", "new", "context"]
    assert lines[0] == {"side": "context", "old_line": 1, "new_line": 1, "text": "unchanged"}
    assert lines[1] == {"side": "old", "old_line": 2, "new_line": None, "text": "old line"}
    assert lines[2] == {"side": "new", "old_line": None, "new_line": 2, "text": "new line"}
    assert lines[3] == {"side": "context", "old_line": 3, "new_line": 3, "text": "trailing"}


def test_parse_added():
    files = parse_unified_diff(ADDED_DIFF)
    assert files[0]["path"] == "new.py"
    assert files[0]["status"] == "added"
    assert [ln["new_line"] for ln in files[0]["hunks"][0]["lines"]] == [1, 2]


def test_parse_deleted():
    files = parse_unified_diff(DELETED_DIFF)
    assert files[0]["path"] == "gone.py"
    assert files[0]["status"] == "deleted"
    assert files[0]["hunks"][0]["lines"][0]["side"] == "old"


def test_parse_empty():
    assert parse_unified_diff("") == []


def test_parse_ignores_preamble():
    # Any line before the first "diff --git" is skipped (covers the guard).
    assert parse_unified_diff("garbage before any file\n") == []


def test_parse_malformed_hunk_header():
    # A line starting with "@@" that doesn't match the hunk regex is skipped.
    diff = "diff --git a/foo.py b/foo.py\n--- a/foo.py\n+++ b/foo.py\n@@ malformed @@\n+added\n"
    files = parse_unified_diff(diff)
    # No hunks because the only hunk header was malformed.
    assert files[0]["hunks"] == []


def _commit_initial(path):
    (path / "tracked.txt").write_text("one\ntwo\nthree\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


def test_build_untracked_file(tmp_path):
    (tmp_path / "brand.txt").write_text("alpha\nbeta\n")
    f = build_untracked_file("brand.txt", str(tmp_path))
    assert f["status"] == "untracked"
    assert f["old_path"] is None
    lines = f["hunks"][0]["lines"]
    assert [ln["text"] for ln in lines] == ["alpha", "beta"]
    assert all(ln["side"] == "new" for ln in lines)


def test_build_untracked_empty_file(tmp_path):
    (tmp_path / "empty.txt").write_text("")
    f = build_untracked_file("empty.txt", str(tmp_path))
    assert f["hunks"] == []


def test_build_untracked_unreadable_path(tmp_path):
    # A directory cannot be read as text -> OSError branch -> empty content.
    (tmp_path / "adir").mkdir()
    f = build_untracked_file("adir", str(tmp_path))
    assert f["hunks"] == []


def test_get_untracked_files(tmp_path):
    _init_repo(tmp_path)
    _commit_initial(tmp_path)
    (tmp_path / "extra.txt").write_text("new\n")
    assert get_untracked_files(str(tmp_path)) == ["extra.txt"]


def test_collect_diff_combines_tracked_and_untracked(tmp_path):
    _init_repo(tmp_path)
    _commit_initial(tmp_path)
    (tmp_path / "tracked.txt").write_text("one\nCHANGED\nthree\n")
    (tmp_path / "extra.txt").write_text("brand new\n")
    data = collect_diff(str(tmp_path))
    assert data["has_changes"] is True
    statuses = {f["path"]: f["status"] for f in data["files"]}
    assert statuses["tracked.txt"] == "modified"
    assert statuses["extra.txt"] == "untracked"


def test_collect_diff_no_changes(tmp_path):
    _init_repo(tmp_path)
    _commit_initial(tmp_path)
    data = collect_diff(str(tmp_path))
    assert data["has_changes"] is False
    assert data["files"] == []


def test_collect_diff_not_a_repo(tmp_path):
    with pytest.raises(NotAGitRepo):
        collect_diff(str(tmp_path))


def _make_branch_with_commit(path):
    """main with an initial commit, then a feature branch with one committed change."""
    _init_repo(path)
    _commit_initial(path)
    subprocess.run(["git", "branch", "-M", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "feat"], cwd=path, check=True, capture_output=True)
    (path / "tracked.txt").write_text("one\nBRANCHCHANGE\nthree\n")
    subprocess.run(
        ["git", "commit", "-am", "branch change"], cwd=path, check=True, capture_output=True
    )


def test_resolve_base_prefers_existing_default(tmp_path):
    from collect import resolve_base

    _make_branch_with_commit(tmp_path)
    assert resolve_base(str(tmp_path)) == "main"


def test_resolve_base_none_when_no_default(tmp_path):
    from collect import resolve_base

    _init_repo(tmp_path)
    _commit_initial(tmp_path)
    # Rename the only branch to a non-standard name so no candidate ref matches.
    subprocess.run(["git", "branch", "-M", "wip"], cwd=tmp_path, check=True, capture_output=True)
    assert resolve_base(str(tmp_path)) is None


def test_collect_diff_base_mode_shows_committed_branch_changes(tmp_path):
    _make_branch_with_commit(tmp_path)
    data = collect_diff(str(tmp_path), base="main")
    assert data["has_changes"] is True
    assert data["files"][0]["path"] == "tracked.txt"


def test_collect_diff_base_mode_excludes_untracked(tmp_path):
    _make_branch_with_commit(tmp_path)
    (tmp_path / "untracked.txt").write_text("noise\n")
    data = collect_diff(str(tmp_path), base="main")
    paths = [f["path"] for f in data["files"]]
    assert "untracked.txt" not in paths
