#!/usr/bin/env python3
"""
ABOUTME: Generates a human-readable before/after change summary between original and optimized resumes.
ABOUTME: Outputs a markdown change report grouped by resume section using difflib.
"""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path


def split_into_sections(text: str) -> dict:
    """Split resume text into named sections."""
    sections = {}
    current_heading = "Header"
    current_lines = []

    heading_re = re.compile(r"^(#{1,3})\s+(.+)$")

    for line in text.split("\n"):
        match = heading_re.match(line)
        if match:
            # Save previous section
            sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    sections[current_heading] = "\n".join(current_lines).strip()
    return sections


def generate_section_diff(original: str, optimized: str, section_name: str) -> dict:
    """Generate a diff for a single section."""
    if original == optimized:
        return {
            "section": section_name,
            "changed": False,
            "summary": "No changes",
            "diff_lines": [],
        }

    original_lines = original.splitlines(keepends=True)
    optimized_lines = optimized.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        original_lines,
        optimized_lines,
        fromfile=f"original/{section_name}",
        tofile=f"optimized/{section_name}",
        lineterm="",
    ))

    # Count additions and removals
    additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removals = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

    # Word-level changes
    original_words = set(original.lower().split())
    optimized_words = set(optimized.lower().split())
    words_added = optimized_words - original_words
    words_removed = original_words - optimized_words

    return {
        "section": section_name,
        "changed": True,
        "lines_added": additions,
        "lines_removed": removals,
        "words_added": sorted(list(words_added))[:20],
        "words_removed": sorted(list(words_removed))[:20],
        "diff_lines": [line.rstrip() for line in diff],
    }


def generate_markdown_report(original_path: str, optimized_path: str) -> str:
    """Generate a full markdown change report."""
    orig_file = Path(original_path).expanduser()
    opt_file = Path(optimized_path).expanduser()

    if not orig_file.exists():
        return f"Error: Original file not found: {original_path}"
    if not opt_file.exists():
        return f"Error: Optimized file not found: {optimized_path}"

    original_text = orig_file.read_text(encoding="utf-8")
    optimized_text = opt_file.read_text(encoding="utf-8")

    original_sections = split_into_sections(original_text)
    optimized_sections = split_into_sections(optimized_text)

    # Track all section names in order
    all_sections = list(dict.fromkeys(
        list(original_sections.keys()) + list(optimized_sections.keys())
    ))

    report_lines = [
        "# Resume Customization Change Report",
        "",
        f"**Original**: `{orig_file.name}`",
        f"**Optimized**: `{opt_file.name}`",
        "",
    ]

    # Overall stats
    orig_words = len(original_text.split())
    opt_words = len(optimized_text.split())
    word_delta = opt_words - orig_words

    report_lines.extend([
        "## Overview",
        "",
        f"| Metric | Original | Optimized | Delta |",
        f"|--------|----------|-----------|-------|",
        f"| Word count | {orig_words} | {opt_words} | {word_delta:+d} |",
        f"| Sections | {len(original_sections)} | {len(optimized_sections)} | {len(optimized_sections) - len(original_sections):+d} |",
        "",
    ])

    # Per-section diffs
    changed_sections = []
    unchanged_sections = []

    for section_name in all_sections:
        orig_content = original_sections.get(section_name, "")
        opt_content = optimized_sections.get(section_name, "")
        diff_data = generate_section_diff(orig_content, opt_content, section_name)

        if diff_data["changed"]:
            changed_sections.append(diff_data)
        else:
            unchanged_sections.append(section_name)

    # Summary
    report_lines.extend([
        "## Changes Summary",
        "",
        f"**Sections modified**: {len(changed_sections)}",
        f"**Sections unchanged**: {len(unchanged_sections)}",
        "",
    ])

    if unchanged_sections:
        report_lines.append(f"**Unchanged**: {', '.join(unchanged_sections)}")
        report_lines.append("")

    # Detailed changes
    for diff_data in changed_sections:
        report_lines.extend([
            f"### {diff_data['section']}",
            "",
            f"- Lines added: **{diff_data['lines_added']}**",
            f"- Lines removed: **{diff_data['lines_removed']}**",
        ])

        if diff_data.get("words_added"):
            report_lines.append(f"- New keywords: {', '.join(diff_data['words_added'][:10])}")
        if diff_data.get("words_removed"):
            report_lines.append(f"- Removed words: {', '.join(diff_data['words_removed'][:10])}")

        report_lines.append("")

        # Include the actual diff
        if diff_data["diff_lines"]:
            report_lines.append("```diff")
            for line in diff_data["diff_lines"]:
                report_lines.append(line)
            report_lines.append("```")
            report_lines.append("")

    return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description="Generate resume diff report")
    parser.add_argument("--original", required=True, help="Path to original resume")
    parser.add_argument("--optimized", required=True, help="Path to optimized resume")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown",
                        help="Output format (default: markdown)")
    args = parser.parse_args()

    if args.format == "json":
        orig_text = Path(args.original).expanduser().read_text(encoding="utf-8")
        opt_text = Path(args.optimized).expanduser().read_text(encoding="utf-8")
        orig_sections = split_into_sections(orig_text)
        opt_sections = split_into_sections(opt_text)

        all_sections = list(dict.fromkeys(
            list(orig_sections.keys()) + list(opt_sections.keys())
        ))

        diffs = []
        for name in all_sections:
            diff = generate_section_diff(
                orig_sections.get(name, ""),
                opt_sections.get(name, ""),
                name,
            )
            diffs.append(diff)

        print(json.dumps({"sections": diffs}, indent=2))
    else:
        report = generate_markdown_report(args.original, args.optimized)
        print(report)


if __name__ == "__main__":
    main()
