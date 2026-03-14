#!/usr/bin/env python3
"""
ABOUTME: Parses a markdown resume into structured sections with metadata.
ABOUTME: Outputs JSON with identified sections, their content, and classification.
"""

import json
import re
import sys
from pathlib import Path


# Section name normalization map — handles common resume heading variations
SECTION_ALIASES = {
    "summary": "summary",
    "professional summary": "summary",
    "executive summary": "summary",
    "about": "summary",
    "about me": "summary",
    "profile": "summary",
    "objective": "summary",
    "career objective": "summary",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "work history": "experience",
    "employment history": "experience",
    "employment": "experience",
    "relevant experience": "experience",
    "skills": "skills",
    "technical skills": "skills",
    "core competencies": "skills",
    "competencies": "skills",
    "technologies": "skills",
    "tech stack": "skills",
    "tools & technologies": "skills",
    "tools and technologies": "skills",
    "areas of expertise": "skills",
    "education": "education",
    "academic background": "education",
    "certifications": "education",
    "education & certifications": "education",
    "education and certifications": "education",
    "training": "education",
    "projects": "projects",
    "personal projects": "projects",
    "side projects": "projects",
    "portfolio": "projects",
    "selected projects": "projects",
    "open source": "projects",
    "publications": "publications",
    "research": "publications",
    "papers": "publications",
    "awards": "awards",
    "honors": "awards",
    "honors & awards": "awards",
    "achievements": "awards",
    "volunteer": "volunteer",
    "volunteering": "volunteer",
    "community": "volunteer",
    "community involvement": "volunteer",
    "languages": "languages",
    "interests": "interests",
    "hobbies": "interests",
    "references": "references",
    "contact": "contact",
    "contact information": "contact",
}

# Heading patterns:
# - H1 (#) is the candidate name
# - H2 (##) defines resume sections (Summary, Experience, Skills, etc.)
# - H3 (###) defines entries within sections (job roles, projects) — stays as content
H1_RE = re.compile(r"^#\s+(.+)$")
SECTION_RE = re.compile(r"^##\s+(.+)$")
UNDERLINE_RE = re.compile(r"^[=\-]{3,}$")


def classify_section(heading: str) -> str:
    """Normalize a heading to a standard section type."""
    normalized = heading.strip().lower()
    # Strip leading/trailing special characters
    normalized = re.sub(r"^[#*_\-]+|[#*_\-]+$", "", normalized).strip()
    return SECTION_ALIASES.get(normalized, "other")


def extract_contact_info(text: str) -> dict:
    """Extract contact information from resume header area."""
    contact = {}
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if email_match:
        contact["email"] = email_match.group()

    phone_match = re.search(r"[\+]?[\d\s\-\(\)]{10,}", text)
    if phone_match:
        contact["phone"] = phone_match.group().strip()

    # LinkedIn URL
    linkedin_match = re.search(r"linkedin\.com/in/[\w\-]+", text)
    if linkedin_match:
        contact["linkedin"] = linkedin_match.group()

    # GitHub URL
    github_match = re.search(r"github\.com/[\w\-]+", text)
    if github_match:
        contact["github"] = github_match.group()

    # Portfolio/website URL
    url_match = re.search(r"https?://(?!linkedin|github)[\w\-./]+", text)
    if url_match:
        contact["website"] = url_match.group()

    return contact


def count_bullets(text: str) -> int:
    """Count bullet points in text."""
    return len(re.findall(r"^\s*[-*•]\s", text, re.MULTILINE))


def count_quantified_bullets(text: str) -> int:
    """Count bullets that contain quantifiable metrics."""
    bullets = re.findall(r"^\s*[-*•]\s+(.+)$", text, re.MULTILINE)
    quantified = 0
    for bullet in bullets:
        if re.search(r"\d+[%$xX]|\d+\s*(percent|million|billion|thousand|users|clients|projects|teams|members)", bullet):
            quantified += 1
    return quantified


def parse_resume(filepath: str) -> dict:
    """Parse a markdown resume into structured sections."""
    path = Path(filepath).expanduser()
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    sections = []
    current_heading = None
    current_lines = []
    name = ""
    header_lines = []  # Lines before first ## section heading
    found_first_section = False

    for i, line in enumerate(lines):
        # Check for H1 heading (candidate name)
        h1_match = H1_RE.match(line)
        if h1_match:
            name = h1_match.group(1).strip()
            if not found_first_section:
                # H1 before any section — part of header
                header_lines.append(line)
            else:
                # H1 inside a section (unusual but handle it)
                current_lines.append(line)
            continue

        # Check for H2 heading (section divider)
        section_match = SECTION_RE.match(line)

        # Check for underline-style heading
        is_underline_heading = False
        if (
            not section_match
            and i > 0
            and UNDERLINE_RE.match(line)
            and lines[i - 1].strip()
        ):
            is_underline_heading = True
            heading_text = lines[i - 1].strip()

        if section_match:
            heading_text = section_match.group(1).strip()

        if section_match or is_underline_heading:
            if not found_first_section:
                found_first_section = True
                # Everything before the first section is header/contact
                if is_underline_heading and current_lines:
                    # Remove the line that became the heading
                    current_lines = current_lines[:-1]
                header_lines.extend(current_lines)
            else:
                # Save previous section
                if current_heading is not None:
                    content = "\n".join(current_lines).strip()
                    section_type = classify_section(current_heading)
                    sections.append({
                        "heading": current_heading,
                        "type": section_type,
                        "content": content,
                        "bullet_count": count_bullets(content),
                        "quantified_bullets": count_quantified_bullets(content),
                        "word_count": len(content.split()),
                    })

            current_heading = heading_text
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_heading is not None:
        content = "\n".join(current_lines).strip()
        section_type = classify_section(current_heading)
        sections.append({
            "heading": current_heading,
            "type": section_type,
            "content": content,
            "bullet_count": count_bullets(content),
            "quantified_bullets": count_quantified_bullets(content),
            "word_count": len(content.split()),
        })

    # Extract name from H1 heading or first non-empty header line
    header_text = "\n".join(header_lines).strip()
    if not name:
        for hl in header_lines:
            stripped = hl.strip()
            if stripped and not re.match(r"[\w.+-]+@", stripped):
                name = re.sub(r"^#+\s*", "", stripped)
                break

    total_words = sum(s["word_count"] for s in sections) + len(header_text.split())
    total_bullets = sum(s["bullet_count"] for s in sections)
    total_quantified = sum(s["quantified_bullets"] for s in sections)

    result = {
        "file": str(path),
        "name": name,
        "contact": extract_contact_info(header_text),
        "header": header_text,
        "sections": sections,
        "metadata": {
            "total_sections": len(sections),
            "total_words": total_words,
            "total_bullets": total_bullets,
            "quantified_bullets": total_quantified,
            "quantification_rate": round(total_quantified / total_bullets * 100, 1) if total_bullets > 0 else 0,
            "section_types": [s["type"] for s in sections],
            "estimated_pages": max(1, round(total_words / 500)),
        },
    }
    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: parse_resume.py <resume.md>"}))
        sys.exit(1)

    result = parse_resume(sys.argv[1])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
