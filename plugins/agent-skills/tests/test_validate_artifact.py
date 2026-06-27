# ABOUTME: Tests for the self-contained-HTML validator the visual skills use to
# ABOUTME: prove a generated plan/recap has no external resource dependencies.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validate_artifact import validate_artifact  # noqa: E402

GOOD = (
    '<!doctype html><html><head><meta charset="utf-8"><title>P</title>'
    "<style>:root{--x:0}</style></head>"
    '<body><h1>Plan</h1><img src="data:image/png;base64,AAAA"><script>0</script></body></html>'
)


def test_clean_file_has_no_violations():
    assert validate_artifact(GOOD) == []


def test_flags_missing_html_root():
    assert any("required HTML" in v for v in validate_artifact("<div>no root</div>"))


def test_flags_external_script():
    v = validate_artifact(GOOD.replace("<script>0</script>", '<script src="https://cdn.example.com/x.js"></script>'))
    assert any("external reference" in x and "cdn.example.com" in x for x in v)


def test_flags_external_link_stylesheet():
    v = validate_artifact(GOOD.replace("</head>", '<link rel="stylesheet" href="https://fonts.googleapis.com/x"></head>'))
    assert any("external reference" in x for x in v)


def test_flags_protocol_relative_and_css_url():
    assert validate_artifact(GOOD.replace("<h1>Plan</h1>", '<img src="//evil.example/x.png">'))
    assert validate_artifact(GOOD.replace("--x:0", "--x:0;background:url(http://evil.example/b.png)"))


def test_flags_external_import_string_form():
    v = validate_artifact(GOOD.replace("</head>", '<style>@import "https://fonts.googleapis.com/x";</style></head>'))
    assert any("external reference" in x for x in v)


def test_flags_external_srcset():
    v = validate_artifact(GOOD.replace("<h1>Plan</h1>", '<img srcset="https://x.co/i.png 1x">'))
    assert any("external reference" in x for x in v)


def test_allows_navigational_anchor_link():
    # A navigational <a href="https://..."> loads nothing and must NOT be flagged.
    assert validate_artifact(GOOD.replace("<h1>Plan</h1>", '<a href="https://example.com">pr</a>')) == []


def test_flags_missing_charset():
    assert any("charset" in v for v in validate_artifact(GOOD.replace('<meta charset="utf-8">', "")))


def test_flags_missing_title():
    assert any("title" in v.lower() for v in validate_artifact(GOOD.replace("<title>P</title>", "")))


def test_flags_missing_body():
    assert any("body" in v.lower() for v in validate_artifact(GOOD.replace("<body>", "").replace("</body>", "")))
