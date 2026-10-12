# ABOUTME: Tests doc_refs.py against real git repos: which references count as paths, how they resolve, and which
# ABOUTME: docs come back with missing or stale references, core docs last.
import json

import doc_refs
import pytest
from conftest import commit, run_git


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    run_git(root, "init", "-q", "-b", "main")
    run_git(root, "config", "user.email", "t@example.com")
    run_git(root, "config", "user.name", "Tester")
    return root


@pytest.mark.parametrize(
    ("text", "refs"),
    [
        ("See [the guide](docs/guide.md#setup) and [site](https://x.dev).", ["docs/guide.md"]),
        ("[mail](mailto:a@b.c)", []),
        ("Run `src/app.py`, edit `./config.toml`, open `scripts/`.", ["src/app.py", "config.toml", "scripts/"]),
        ("`os.path` and `make check` and `True` are not paths.", []),
        ("`/verify`, `--flag`, `${ROOT}/x.py`, `~/a.md`, `a/<n>.md`, `git:x/y`, `https://a.b/c`", []),
        ("[a](x.md) then `x.md` again", ["x.md"]),
    ],
    ids=["links", "mailto", "code paths", "code non-paths", "placeholders", "deduplicated"],
)
def test_path_refs_keeps_only_what_reads_as_a_repo_path(text, refs):
    assert doc_refs.path_refs(text) == refs


def test_scan_reports_missing_and_stale_references_with_core_docs_last(repo):
    commit(
        repo,
        {
            "README.md": "Start with `src/app.py`.\n",
            "docs/guide.md": "Entry: `src/app.py`. Config: [config](../config.toml). Old: `src/gone.py`.\n",
            "docs/self.md": "This file is `docs/self.md`.\n",
            "src/app.py": "print(1)\n",
            "config.toml": "a = 1\n",
        },
        "first",
    )
    commit(repo, {"src/app.py": "print(2)\n"}, "change app")
    commit(repo, {"src/app.py": "print(3)\n"}, "change app again")

    docs = doc_refs.scan(repo)

    assert [(d.path, d.core) for d in docs] == [("docs/guide.md", False), ("docs/self.md", False), ("README.md", True)]
    guide, own, readme = docs
    assert (guide.refs, guide.missing, guide.stale) == (3, ["src/gone.py"], {"src/app.py": 2})
    assert (own.missing, own.stale) == ([], {})
    assert readme.stale == {"src/app.py": 2}


def test_scan_resolves_from_any_directory_above_the_doc_and_by_unique_file_name(repo):
    commit(
        repo,
        {
            "pkg/docs/notes.md": "`scripts/run.py`, `run.py`, `util.py`, `nowhere.py`\n",
            "pkg/scripts/run.py": "",
            "a/util.py": "",
            "b/util.py": "",
        },
        "first",
    )
    commit(repo, {"pkg/scripts/run.py": "x = 1\n", "a/util.py": "x = 1\n"}, "change")

    (notes,) = doc_refs.scan(repo)

    assert notes.missing == ["nowhere.py"]
    assert notes.stale == {"pkg/scripts/run.py": 1}


def test_scan_skips_excluded_and_broken_docs_and_honours_extra_core_patterns(repo):
    commit(repo, {"skills/x/SKILL.md": "`a.py`\n", "docs/arch.md": "`b.py`\n", "notes.md": "`c.py`\n"}, "first")
    (repo / "dangling.md").symlink_to("missing-target.md")
    run_git(repo, "add", "dangling.md")
    commit(repo, {}, "add a broken link")

    docs = doc_refs.scan(repo, doc_refs.CORE + ("docs/arch.md",), ("SKILL.md",))

    assert [(d.path, d.core) for d in docs] == [("notes.md", False), ("docs/arch.md", True)]


def test_scan_excludes_whole_directories_but_never_a_core_doc(repo):
    commit(repo, {"plugins/a/README.md": "", "plugins/a/skills/x/notes.md": "", "docs/plugins/plan.md": ""}, "first")

    docs = doc_refs.scan(repo, exclude=("plugins/**",))

    assert [(d.path, d.core) for d in docs] == [("docs/plugins/plan.md", False), ("plugins/a/README.md", True)]


def test_scan_never_calls_an_uncommitted_doc_stale(repo):
    commit(repo, {"src/app.py": ""}, "first")
    commit(repo, {"src/app.py": "x\n"}, "change")
    (repo / "draft.md").write_text("`src/app.py`\n")
    run_git(repo, "add", "draft.md")

    (draft,) = doc_refs.scan(repo)

    assert (draft.missing, draft.stale) == ([], {})


def test_main_prints_json_for_the_repo(repo, capsys):
    commit(repo, {"notes.md": "`gone.py`\n"}, "first")

    assert doc_refs.main(["scan", "--root", str(repo), "--core", "notes.md"]) == 0

    assert json.loads(capsys.readouterr().out) == [
        {"path": "notes.md", "core": True, "refs": 1, "missing": ["gone.py"], "stale": {}}
    ]


def test_main_exits_2_outside_a_git_repo(tmp_path, capsys):
    assert doc_refs.main(["scan", "--root", str(tmp_path), "--exclude", "x.md"]) == 2
    assert "git ls-files failed" in capsys.readouterr().err
