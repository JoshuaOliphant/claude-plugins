# ABOUTME: Tests for extract.py: which comments, handlers, functions, log calls, and diff hunks become units, and their state.
# ABOUTME: Sources are small inline snippets; no model calls.
import pytest
from extract import (
    MAX_SEGMENT_LINES,
    extract_comments,
    extract_hunks,
    extract_source_units,
    is_test_path,
    truncate,
)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/helpers.py", True),
        ("pkg/test_orders.py", True),
        ("pkg/orders_test.py", True),
        ("test_orders.py", True),
        ("pkg/orders.py", False),
    ],
)
def test_is_test_path(path, expected):
    assert is_test_path(path) is expected


def test_truncate_keeps_short_text_and_marks_cut_lines():
    assert truncate("a\nb", max_lines=2) == "a\nb"
    long_text = "\n".join(str(n) for n in range(MAX_SEGMENT_LINES + 5))
    assert truncate(long_text).splitlines()[-1] == "... (5 more lines)"


def test_comments_skip_directives_and_script_block():
    source = (
        "#!/usr/bin/env python\n"
        "# /// script\n"
        '# dependencies = ["x"]\n'
        "# ///\n"
        "# ABOUTME: a module\n"
        "import os  # noqa: F401\n"
        "x = 1  # type: ignore\n"
    )
    assert extract_comments("m.py", source) == []


def test_consecutive_full_line_comments_form_one_block_with_code_context():
    source = "a = 1\nb = 2\n# first line\n# second line\nc = 3\n# unrelated later\nd = 4\n"
    first, second = extract_comments("m.py", source)
    assert first.line == 3
    assert first.state == {
        "comment": "# first line\n# second line",
        "code_before": "a = 1\nb = 2",
        "code_after": "c = 3\nd = 4",
    }
    assert second.state["code_before"] == "a = 1\nb = 2\nc = 3"


def test_inline_comment_is_its_own_unit_and_carries_its_line():
    source = "total = price * 2  # double it\n# next\nx = 1\n"
    inline, full = extract_comments("m.py", source)
    assert inline.state["inline_code"] == "total = price * 2"
    assert inline.name == "# double it"
    assert "inline_code" not in full.state


def test_source_units_cover_functions_handlers_and_log_calls():
    source = '''
import logging
logger = logging.getLogger(__name__)
logger.info("module import")
make_logger().info("not a logger name")


class Store:
    def load(self, path):
        """Read the store."""
        try:
            return open(path).read()
        except FileNotFoundError:
            self.log.warning("missing %s", path)
            return ""
        except:
            raise


async def refresh():
    try:
        pass
    except* ValueError:
        pass
'''
    units = extract_source_units("pkg/store.py", source)
    by_kind = {}
    for unit in units:
        by_kind.setdefault(unit.kind, []).append(unit)

    functions = {unit.name: unit for unit in by_kind["function"]}
    assert set(functions) == {"Store.load", "refresh"}
    assert functions["Store.load"].state["docstring"] == "Read the store."
    assert "docstring" not in functions["refresh"].state

    handler_names = [unit.name for unit in by_kind["handler"]]
    assert handler_names == ["FileNotFoundError", "bare except", "ValueError"]
    assert [unit.facts for unit in by_kind["handler"]] == [
        {"bare": False, "broad": False, "only_statement": None},
        {"bare": True, "broad": False, "only_statement": "Raise"},
        {"bare": False, "broad": False, "only_statement": "Pass"},
    ]
    assert "try:" in by_kind["handler"][0].state["try_statement"]
    assert by_kind["handler"][0].state["handler"].startswith("except FileNotFoundError")

    log_calls = by_kind["log_call"]
    assert [unit.name for unit in log_calls] == ["info", "warning"]
    assert "enclosing_function" not in log_calls[0].state
    assert "def load" in log_calls[1].state["enclosing_function"]


DIFF = """diff --git a/pkg/orders.py b/pkg/orders.py
index 1111111..2222222 100644
--- a/pkg/orders.py
+++ b/pkg/orders.py
@@ -3,2 +3,3 @@ def total(order):
     items = order.items
-    return sum(items)
+    time.sleep(1)
+    return sum(items)
@@ -20 +21 @@
 unchanged = True
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-old
+new
--- a/tests/test_orders.py
+++ tests/test_orders.py
@@ -9 +9,0 @@
-    assert total == 42
"""


def test_hunks_keep_python_changes_only_with_removed_and_added_lines():
    first, second = extract_hunks(DIFF)
    assert (first.kind, first.path, first.line) == ("hunk", "pkg/orders.py", 3)
    assert first.state["removed"] == "    return sum(items)"
    assert first.state["added"] == "    time.sleep(1)\n    return sum(items)"
    assert first.state["hunk"].startswith("     items = order.items")
    assert (second.path, second.state["removed"], second.state["added"]) == (
        "tests/test_orders.py",
        "    assert total == 42",
        "",
    )


def test_comments_resume_after_a_closed_script_block():
    source = '# /// script\n# dependencies = ["x"]\n# ///\n# real comment\nx = 1\n'
    [unit] = extract_comments("m.py", source)
    assert unit.state["comment"] == "# real comment"


def test_unclosed_script_block_does_not_swallow_later_comments():
    source = "# /// script\nx = 1\n# still a comment\n"
    assert [unit.state["comment"] for unit in extract_comments("m.py", source)] == [
        "# /// script",
        "# still a comment",
    ]


def test_log_calls_match_logger_names_not_substrings():
    source = """
import logging
catalog.error("not a logger")
dialog.warn("not a logger")
backlog.info("not a logger")
loggers[0].info("not a logger name")
logging.getLogger(__name__).info("from getLogger")
self._logger.error("suffix match")
audit_log.warning("suffix match")
"""
    calls = [unit.state["log_call"] for unit in extract_source_units("m.py", source)]
    assert calls == [
        'logging.getLogger(__name__).info("from getLogger")',
        'self._logger.error("suffix match")',
        'audit_log.warning("suffix match")',
    ]


def test_handler_catching_a_tuple_with_exception_is_broad():
    source = "try:\n    x()\nexcept (ValueError, Exception):\n    pass\n"
    [handler] = [u for u in extract_source_units("m.py", source) if u.kind == "handler"]
    assert handler.facts == {"bare": False, "broad": True, "only_statement": "Pass"}


def test_nested_functions_are_named_by_their_scope():
    source = "class A:\n    def outer(self):\n        def inner():\n            pass\n"
    names = [u.name for u in extract_source_units("m.py", source) if u.kind == "function"]
    assert names == ["A.outer", "A.outer.inner"]


def test_hunks_for_a_deleted_file_use_the_old_path():
    diff = (
        "--- a/tests/test_x.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n"
        "-def test_x():\n-    assert x == 1\n"
    )
    [hunk] = extract_hunks(diff)
    assert hunk.path == "tests/test_x.py"
    assert hunk.state["removed"] == "def test_x():\n    assert x == 1"


def test_hunk_body_lines_that_look_like_headers_stay_in_the_hunk():
    diff = (
        "--- a/m.py\n"
        "+++ b/m.py\n"
        "@@ -2,2 +2,2 @@\n"
        " x = 1\n"
        "--- sql comment\n"
        "\\ No newline at end of file\n"
        "+++ new heading\n"
        "\\ No newline at end of file\n"
    )
    [hunk] = extract_hunks(diff)
    assert hunk.path == "m.py"
    assert hunk.state["removed"] == "-- sql comment"
    assert hunk.state["added"] == "++ new heading"
    assert "No newline" not in hunk.state["hunk"]


def test_combined_diff_headers_are_ignored():
    diff = "--- a/m.py\n+++ b/m.py\n@@@ -1,1 -1,1 +1,1 @@@\n- x\n+ y\n"
    assert extract_hunks(diff) == []
