#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "markdown",
#     "weasyprint",
# ]
# ///
"""
ABOUTME: Converts a markdown resume to a professionally styled PDF.
ABOUTME: Uses pandoc (if available) or weasyprint with custom CSS for clean output.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# Professional resume CSS — single column, clean typography, ATS-friendly
RESUME_CSS = """
@page {
    size: letter;
    margin: 0.6in 0.7in 0.6in 0.7in;
}

body {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.4;
    color: #1a1a1a;
    max-width: none;
}

h1 {
    font-size: 20pt;
    font-weight: 700;
    margin-bottom: 2pt;
    color: #000;
    text-align: center;
    border-bottom: none;
}

/* Contact line right after h1 */
h1 + p {
    text-align: center;
    font-size: 9pt;
    color: #444;
    margin-top: 0;
    margin-bottom: 12pt;
}

h2 {
    font-size: 12pt;
    font-weight: 700;
    color: #000;
    border-bottom: 1.5pt solid #000;
    padding-bottom: 2pt;
    margin-top: 14pt;
    margin-bottom: 6pt;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
}

h3 {
    font-size: 10.5pt;
    font-weight: 700;
    color: #1a1a1a;
    margin-top: 10pt;
    margin-bottom: 2pt;
}

p {
    margin: 2pt 0;
}

/* Job title + dates line */
p strong {
    font-weight: 600;
}

ul {
    margin: 3pt 0 6pt 0;
    padding-left: 16pt;
}

li {
    margin-bottom: 2pt;
    font-size: 9.5pt;
    line-height: 1.35;
}

/* Skills section — tighter spacing */
h2 + ul {
    margin-top: 2pt;
}

h2 + ul li {
    margin-bottom: 1pt;
}

/* Links */
a {
    color: #1a1a1a;
    text-decoration: none;
}

/* Code/monospace for repo names */
code {
    font-family: "SF Mono", "Menlo", "Monaco", monospace;
    font-size: 8.5pt;
    color: #333;
    background: none;
    padding: 0;
}

/* Don't break job entries across pages */
h3, h3 + p, h3 + p + ul {
    page-break-inside: avoid;
}

/* Keep bullets with their heading */
h3 + ul, p + ul {
    page-break-before: avoid;
}
"""

# Pandoc LaTeX template variables for clean resume output
PANDOC_VARS = [
    "-V", "geometry:margin=0.65in",
    "-V", "fontsize=10pt",
    "-V", "mainfont=Helvetica Neue",
    "-V", "monofont=Menlo",
    "-V", "linestretch=1.15",
    "-V", "urlcolor=black",
    "-V", "linkcolor=black",
]


def convert_with_pandoc(md_path: Path, pdf_path: Path) -> bool:
    """Convert markdown to PDF using pandoc."""
    pandoc = shutil.which("pandoc")
    if not pandoc:
        return False

    # Check if LaTeX is available for best quality
    has_latex = shutil.which("xelatex") or shutil.which("pdflatex")

    cmd = [pandoc, str(md_path), "-o", str(pdf_path)]

    if has_latex:
        # Use LaTeX engine for best typography
        cmd.extend(["--pdf-engine=xelatex"])
        cmd.extend(PANDOC_VARS)
    else:
        # Fall back to pandoc's built-in HTML→PDF
        # Write CSS to temp file
        css_file = tempfile.NamedTemporaryFile(suffix=".css", mode="w", delete=False)
        css_file.write(RESUME_CSS)
        css_file.close()
        cmd.extend(["--css", css_file.name, "--pdf-engine=weasyprint"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return True
        # If LaTeX/weasyprint failed, try simpler pandoc HTML output
        print(f"Pandoc warning: {result.stderr.strip()}", file=sys.stderr)
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def convert_with_weasyprint(md_path: Path, pdf_path: Path) -> bool:
    """Convert markdown to PDF using weasyprint (via uv inline deps)."""
    try:
        import markdown
        import weasyprint
    except ImportError:
        return False

    md_text = md_path.read_text(encoding="utf-8")

    # Convert markdown to HTML
    html_body = markdown.markdown(md_text, extensions=["extra", "smarty"])

    # Wrap in full HTML document with CSS
    html_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{RESUME_CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    # Generate PDF
    doc = weasyprint.HTML(string=html_doc)
    doc.write_pdf(str(pdf_path))
    return True


def convert_to_html(md_path: Path, html_path: Path) -> bool:
    """Convert markdown to styled HTML as a fallback."""
    try:
        import markdown
        md_text = md_path.read_text(encoding="utf-8")
        html_body = markdown.markdown(md_text, extensions=["extra", "smarty"])
    except ImportError:
        # Manual basic markdown→HTML if markdown library unavailable
        md_text = md_path.read_text(encoding="utf-8")
        import re
        html_body = md_text
        # Basic conversions
        html_body = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html_body, flags=re.MULTILINE)
        html_body = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html_body, flags=re.MULTILINE)
        html_body = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html_body, flags=re.MULTILINE)
        html_body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html_body)
        html_body = re.sub(r"^- (.+)$", r"<li>\1</li>", html_body, flags=re.MULTILINE)
        html_body = re.sub(r"(<li>.*</li>)", r"<ul>\1</ul>", html_body, flags=re.DOTALL)
        html_body = html_body.replace("\n\n", "\n<p>\n")

    html_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Resume</title>
<style>{RESUME_CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    html_path.write_text(html_doc, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description="Convert markdown resume to PDF")
    parser.add_argument("input", help="Path to markdown resume file")
    parser.add_argument("-o", "--output", help="Output PDF path (default: same name with .pdf)")
    parser.add_argument("--html-only", action="store_true",
                        help="Output styled HTML instead of PDF (for manual Print→PDF)")
    parser.add_argument("--open", action="store_true",
                        help="Open the output file after generation")
    args = parser.parse_args()

    md_path = Path(args.input).expanduser().resolve()
    if not md_path.exists():
        print(f"Error: File not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    if args.html_only:
        out_path = Path(args.output) if args.output else md_path.with_suffix(".html")
        if convert_to_html(md_path, out_path):
            print(f"HTML generated: {out_path}")
            if args.open:
                subprocess.run(["open", str(out_path)])
        else:
            print("Error: Failed to generate HTML", file=sys.stderr)
            sys.exit(1)
        return

    pdf_path = Path(args.output) if args.output else md_path.with_suffix(".pdf")

    # Strategy 1: pandoc (best quality if LaTeX available)
    print("Trying pandoc...", file=sys.stderr)
    if convert_with_pandoc(md_path, pdf_path):
        print(f"PDF generated: {pdf_path}")
        if args.open:
            subprocess.run(["open", str(pdf_path)])
        return

    # Strategy 2: weasyprint (good quality, pure Python + system libs)
    print("Pandoc failed, trying weasyprint...", file=sys.stderr)
    if convert_with_weasyprint(md_path, pdf_path):
        print(f"PDF generated: {pdf_path}")
        if args.open:
            subprocess.run(["open", str(pdf_path)])
        return

    # Strategy 3: HTML fallback (open in browser, user does Print→PDF)
    print("PDF engines unavailable, generating styled HTML...", file=sys.stderr)
    html_path = md_path.with_suffix(".html")
    if convert_to_html(md_path, html_path):
        print(f"HTML generated: {html_path}")
        print("Open in browser and use Print → Save as PDF (Cmd+P)", file=sys.stderr)
        if args.open:
            subprocess.run(["open", str(html_path)])
    else:
        print("Error: All conversion methods failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
