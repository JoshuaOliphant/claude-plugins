# ABOUTME: Zero-dependency linter proving a visual-plan/recap HTML artifact is
# ABOUTME: self-contained: valid root/head tags and no external resource loads.
import re
import sys

# External target prefix: absolute http(s) or protocol-relative.
_EXTERNAL = r"(?:https?:|//)"

# Resource-loading forms that must not point at an external target. A plain
# navigational <a href="https://..."> is intentionally NOT matched: it loads
# nothing, so the page still renders fully offline.
_PATTERNS = [
    ("src/srcset/poster", re.compile(rf"\b(?:src|srcset|poster)\s*=\s*[\"']?\s*{_EXTERNAL}", re.I)),
    ("<link href>", re.compile(rf"<link\b[^>]*?\bhref\s*=\s*[\"']?\s*{_EXTERNAL}", re.I)),
    ("css url()", re.compile(rf"url\(\s*[\"']?\s*{_EXTERNAL}", re.I)),
    ("@import", re.compile(rf"@import\s+[\"']\s*{_EXTERNAL}", re.I)),
]

# Known limitation: an external URL shown inside an escaped code sample
# (e.g. &lt;img src="https://..."&gt; in a <pre>) is still flagged. That is an
# accepted false-positive of a regex (not full-parser) check; confirm such a hit
# is inert display text and disregard it.


def validate_artifact(html):
    """Return a list of self-containment violations (empty list == OK)."""
    violations = []

    if not re.search(r"<!doctype html>", html, re.I) and not re.search(r"<html[\s>]", html, re.I):
        violations.append("missing required HTML root (need <!doctype html> or <html>)")
    if not re.search(r"<meta\s+charset", html, re.I):
        violations.append("missing <meta charset> (artifact.md rule 3)")
    if not re.search(r"<title[\s>]", html, re.I):
        violations.append("missing <title> (artifact.md rule 3)")
    if not re.search(r"<body[\s>]", html, re.I):
        violations.append("missing <body> (artifact.md rule 3)")

    for _what, rx in _PATTERNS:
        for m in rx.finditer(html):
            snippet = re.sub(r"\s+", " ", html[m.start():m.start() + 80])
            violations.append(f"external reference (must be inline/data:): {snippet}")
    return violations


def main(argv):
    if len(argv) < 2:
        print("usage: validate_artifact.py <file.html>", file=sys.stderr)
        return 1
    with open(argv[1], encoding="utf-8") as f:
        violations = validate_artifact(f.read())
    if violations:
        print(f"{argv[1]} is not self-contained:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1
    print(f"{argv[1]}: self-contained OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
