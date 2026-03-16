#!/usr/bin/env python3
"""
ABOUTME: Syncs master resume markdown with structured YAML and detects drift between them.
ABOUTME: Maintains a canonical source of truth for resume data at ~/.claude/resume-tailor/.
"""

import json
import re
import sys
from pathlib import Path


PROFILE_DIR = Path.home() / ".claude" / "resume-tailor"
DEFAULT_MASTER_DIR = PROFILE_DIR


def resolve_master_dir() -> Path:
    """Resolve master resume directory from profile config, falling back to default.

    Lookup order:
    1. master_resume_dir in profile.yaml (user-configured path)
    2. Default ~/.claude/resume-tailor/
    """
    profile_file = PROFILE_DIR / "profile.yaml"
    if profile_file.exists():
        content = profile_file.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if line.strip().startswith("master_resume_dir:"):
                configured = line.split(":", 1)[1].strip()
                configured_path = Path(configured).expanduser()
                if configured_path.exists():
                    return configured_path
    return DEFAULT_MASTER_DIR


def get_master_paths() -> tuple[Path, Path]:
    """Return resolved (master_md, master_yaml) paths."""
    master_dir = resolve_master_dir()
    return master_dir / "master-resume.md", master_dir / "master-resume.yaml"


MASTER_MD, MASTER_YAML = get_master_paths()


def parse_master_md(filepath: Path) -> dict:
    """Parse the master resume markdown into structured data."""
    if not filepath.exists():
        return {"error": f"Master resume not found: {filepath}"}

    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    data = {
        "name": "",
        "contact": "",
        "summary": "",
        "experience": [],
        "skills": {},
        "projects": [],
        "education": [],
    }

    # Extract name from H1
    for line in lines:
        h1 = re.match(r"^#\s+(.+)$", line)
        if h1:
            data["name"] = h1.group(1).strip()
            break

    # Extract contact line (first non-empty line after H1 that isn't a heading)
    found_h1 = False
    for line in lines:
        if re.match(r"^#\s+", line):
            found_h1 = True
            continue
        if found_h1 and line.strip() and not re.match(r"^#", line):
            data["contact"] = line.strip()
            break

    # Split into H2 sections
    sections = {}
    current_heading = None
    current_lines = []

    for line in lines:
        h2 = re.match(r"^##\s+(.+)$", line)
        if h2:
            if current_heading:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = h2.group(1).strip()
            current_lines = []
        elif current_heading:
            current_lines.append(line)

    if current_heading:
        sections[current_heading] = "\n".join(current_lines).strip()

    # Parse Summary
    data["summary"] = sections.get("Summary", "")

    # Parse Experience
    exp_text = sections.get("Experience", "")
    if exp_text:
        data["experience"] = parse_experience(exp_text)

    # Parse Skills
    skills_text = sections.get("Skills", "")
    if skills_text:
        data["skills"] = parse_skills(skills_text)

    # Parse Projects
    projects_text = sections.get("AI & Developer Tool Projects", "")
    if projects_text:
        data["projects"] = parse_projects(projects_text)

    # Parse Education
    edu_text = sections.get("Education", "")
    if edu_text:
        data["education"] = parse_education(edu_text)

    return data


def parse_experience(text: str) -> list:
    """Parse experience section into structured job entries."""
    jobs = []
    current_company = ""
    current_title = ""
    current_dates = ""
    current_bullets = []

    for line in text.split("\n"):
        # Company heading (### Company — Location)
        h3 = re.match(r"^###\s+(.+)$", line)
        if h3:
            # Save previous job if exists
            if current_title:
                jobs.append({
                    "company": current_company,
                    "title": current_title,
                    "dates": current_dates,
                    "bullets": current_bullets,
                })
            current_company = h3.group(1).strip()
            current_title = ""
            current_dates = ""
            current_bullets = []
            continue

        # Job title line (**Title** — Dates)
        title_match = re.match(r"^\*\*(.+?)\*\*\s*[—\-–]\s*(.+)$", line)
        if title_match:
            # Save previous job under same company if exists
            if current_title:
                jobs.append({
                    "company": current_company,
                    "title": current_title,
                    "dates": current_dates,
                    "bullets": current_bullets,
                })
            current_title = title_match.group(1).strip()
            current_dates = title_match.group(2).strip()
            current_bullets = []
            continue

        # Bullet point
        bullet_match = re.match(r"^\s*-\s+(.+)$", line)
        if bullet_match and current_title:
            current_bullets.append(bullet_match.group(1).strip())

    # Save last job
    if current_title:
        jobs.append({
            "company": current_company,
            "title": current_title,
            "dates": current_dates,
            "bullets": current_bullets,
        })

    return jobs


def parse_skills(text: str) -> dict:
    """Parse skills section into categorized dict."""
    skills = {}
    for line in text.split("\n"):
        match = re.match(r"^\s*-\s+\*\*(.+?)\*\*:\s*(.+)$", line)
        if match:
            category = match.group(1).strip()
            items = [s.strip() for s in match.group(2).split(",")]
            skills[category] = items
    return skills


def parse_projects(text: str) -> list:
    """Parse projects section into list of project dicts."""
    projects = []
    for line in text.split("\n"):
        match = re.match(r"^\s*-\s+\*\*(.+?)\*\*(?:\s+\(`.+?`\))?\s*:\s*(.+)$", line)
        if match:
            name = match.group(1).strip()
            description = match.group(2).strip()
            # Extract repo name if present
            repo_match = re.search(r"`([^`]+)`", line)
            repo = repo_match.group(1) if repo_match else ""
            projects.append({
                "name": name,
                "repo": repo,
                "description": description,
            })
    return projects


def parse_education(text: str) -> list:
    """Parse education section into list of entries."""
    entries = []
    current = {}
    for line in text.split("\n"):
        # Institution line (**School** — Location)
        inst_match = re.match(r"^\*\*(.+?)\*\*\s*[—\-–]\s*(.+)$", line)
        if inst_match:
            if current:
                entries.append(current)
            current = {
                "institution": inst_match.group(1).strip(),
                "location": inst_match.group(2).strip(),
            }
            continue

        # Degree line
        if current and line.strip() and not line.strip().startswith("**"):
            degree_line = line.strip()
            # Split on | for degree | year
            if "|" in degree_line:
                parts = degree_line.split("|")
                current["degree"] = parts[0].strip()
                current["year"] = parts[1].strip() if len(parts) > 1 else ""
            else:
                current["degree"] = degree_line

    if current:
        entries.append(current)
    return entries


def write_yaml(data: dict, filepath: Path):
    """Write structured resume data as simple YAML."""
    lines = [
        "# Master Resume Data (auto-generated from master-resume.md)",
        "# Edit master-resume.md and run 'master_sync.py sync' to update",
        "",
        f"name: {data['name']}",
        f"contact: {data['contact']}",
        "",
        "summary: >",
    ]

    # Wrap summary
    if data["summary"]:
        for chunk in _wrap_text(data["summary"], 78):
            lines.append(f"  {chunk}")

    lines.append("")

    # Experience
    lines.append("experience:")
    for job in data.get("experience", []):
        lines.append(f"  - company: {job['company']}")
        lines.append(f"    title: {job['title']}")
        lines.append(f"    dates: {job['dates']}")
        lines.append(f"    bullets:")
        for bullet in job.get("bullets", []):
            # Escape any colons in bullet text for YAML safety
            lines.append(f"      - {bullet}")

    lines.append("")

    # Skills
    lines.append("skills:")
    for category, items in data.get("skills", {}).items():
        lines.append(f"  {_yaml_key(category)}:")
        for item in items:
            lines.append(f"    - {item}")

    lines.append("")

    # Projects
    lines.append("projects:")
    for proj in data.get("projects", []):
        lines.append(f"  - name: {proj['name']}")
        if proj.get("repo"):
            lines.append(f"    repo: {proj['repo']}")
        lines.append(f"    description: {proj['description']}")

    lines.append("")

    # Education
    lines.append("education:")
    for edu in data.get("education", []):
        lines.append(f"  - institution: {edu.get('institution', '')}")
        lines.append(f"    degree: {edu.get('degree', '')}")
        if edu.get("location"):
            lines.append(f"    location: {edu['location']}")
        if edu.get("year"):
            lines.append(f"    year: {edu['year']}")

    lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")


def _wrap_text(text: str, width: int) -> list:
    """Simple word-wrap for YAML multi-line strings."""
    words = text.split()
    result = []
    current = []
    length = 0
    for word in words:
        if length + len(word) + 1 > width and current:
            result.append(" ".join(current))
            current = [word]
            length = len(word)
        else:
            current.append(word)
            length += len(word) + 1
    if current:
        result.append(" ".join(current))
    return result


def _yaml_key(text: str) -> str:
    """Convert a category name to a safe YAML key."""
    return text.lower().replace(" & ", "_").replace(" ", "_")


def detect_drift(md_data: dict, yaml_path: Path) -> dict:
    """Compare master markdown data against stored YAML data."""
    if not yaml_path.exists():
        return {
            "status": "no_yaml",
            "message": "No YAML file exists yet. Run 'master_sync.py sync' to create it.",
            "drifts": [],
        }

    # Parse the YAML file to compare
    yaml_text = yaml_path.read_text(encoding="utf-8")
    yaml_data = _parse_sync_yaml(yaml_text)

    drifts = []

    # Compare name
    if md_data.get("name", "") != yaml_data.get("name", ""):
        drifts.append({
            "field": "name",
            "markdown": md_data.get("name", ""),
            "yaml": yaml_data.get("name", ""),
        })

    # Compare contact
    if md_data.get("contact", "") != yaml_data.get("contact", ""):
        drifts.append({
            "field": "contact",
            "markdown": md_data.get("contact", ""),
            "yaml": yaml_data.get("contact", ""),
        })

    # Compare experience (by job count and titles)
    md_jobs = md_data.get("experience", [])
    yaml_jobs = yaml_data.get("experience", [])

    if len(md_jobs) != len(yaml_jobs):
        drifts.append({
            "field": "experience.count",
            "markdown": f"{len(md_jobs)} jobs",
            "yaml": f"{len(yaml_jobs)} jobs",
        })

    # Compare each job by title
    md_titles = {j["title"] for j in md_jobs}
    yaml_titles = {j.get("title", "") for j in yaml_jobs}

    only_in_md = md_titles - yaml_titles
    only_in_yaml = yaml_titles - md_titles

    if only_in_md:
        drifts.append({
            "field": "experience.titles",
            "only_in_markdown": sorted(only_in_md),
            "note": "Jobs in markdown but not in YAML",
        })
    if only_in_yaml:
        drifts.append({
            "field": "experience.titles",
            "only_in_yaml": sorted(only_in_yaml),
            "note": "Jobs in YAML but not in markdown",
        })

    # Compare bullet counts per matching job
    for md_job in md_jobs:
        for yaml_job in yaml_jobs:
            if md_job["title"] == yaml_job.get("title", ""):
                md_count = len(md_job.get("bullets", []))
                yaml_count = len(yaml_job.get("bullets", []))
                if md_count != yaml_count:
                    drifts.append({
                        "field": f"experience.bullets({md_job['title'][:40]})",
                        "markdown": f"{md_count} bullets",
                        "yaml": f"{yaml_count} bullets",
                    })
                break

    # Compare skill categories (normalize keys for comparison)
    md_skills = {_yaml_key(k) for k in md_data.get("skills", {}).keys()}
    yaml_skills = set(yaml_data.get("skills", {}).keys())

    if md_skills != yaml_skills:
        only_md = md_skills - yaml_skills
        only_yaml = yaml_skills - md_skills
        if only_md or only_yaml:
            drift_entry = {"field": "skills.categories"}
            if only_md:
                drift_entry["only_in_markdown"] = sorted(only_md)
            if only_yaml:
                drift_entry["only_in_yaml"] = sorted(only_yaml)
            drifts.append(drift_entry)

    # Compare project counts
    md_projs = md_data.get("projects", [])
    yaml_projs = yaml_data.get("projects", [])

    if len(md_projs) != len(yaml_projs):
        drifts.append({
            "field": "projects.count",
            "markdown": f"{len(md_projs)} projects",
            "yaml": f"{len(yaml_projs)} projects",
        })

    # Compare project names
    md_proj_names = {p["name"] for p in md_projs}
    yaml_proj_names = {p.get("name", "") for p in yaml_projs}

    if md_proj_names != yaml_proj_names:
        only_md = md_proj_names - yaml_proj_names
        only_yaml = yaml_proj_names - md_proj_names
        if only_md or only_yaml:
            drift_entry = {"field": "projects.names"}
            if only_md:
                drift_entry["only_in_markdown"] = sorted(only_md)
            if only_yaml:
                drift_entry["only_in_yaml"] = sorted(only_yaml)
            drifts.append(drift_entry)

    # Compare education count
    md_edu = md_data.get("education", [])
    yaml_edu = yaml_data.get("education", [])

    if len(md_edu) != len(yaml_edu):
        drifts.append({
            "field": "education.count",
            "markdown": f"{len(md_edu)} entries",
            "yaml": f"{len(yaml_edu)} entries",
        })

    status = "in_sync" if not drifts else "drifted"
    message = "Master markdown and YAML are in sync." if not drifts else f"Found {len(drifts)} drift(s) between markdown and YAML."

    return {
        "status": status,
        "message": message,
        "drifts": drifts,
    }


def _parse_sync_yaml(text: str) -> dict:
    """Parse the structured YAML back into comparable dict format."""
    data = {
        "name": "",
        "contact": "",
        "summary": "",
        "experience": [],
        "skills": {},
        "projects": [],
        "education": [],
    }

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("#") or not stripped:
            i += 1
            continue

        if stripped.startswith("name:"):
            data["name"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("contact:"):
            data["contact"] = stripped.split(":", 1)[1].strip()
        elif stripped == "experience:":
            i += 1
            data["experience"], i = _parse_yaml_experience(lines, i)
            continue
        elif stripped == "skills:":
            i += 1
            data["skills"], i = _parse_yaml_skills(lines, i)
            continue
        elif stripped == "projects:":
            i += 1
            data["projects"], i = _parse_yaml_projects(lines, i)
            continue
        elif stripped == "education:":
            i += 1
            data["education"], i = _parse_yaml_education(lines, i)
            continue

        i += 1

    return data


def _parse_yaml_experience(lines: list, i: int) -> tuple:
    """Parse experience entries from YAML lines."""
    jobs = []
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("- company:"):
            job = {"company": line.strip().split(":", 1)[1].strip(), "title": "", "dates": "", "bullets": []}
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("- company:") and lines[i].startswith("    "):
                stripped = lines[i].strip()
                if stripped.startswith("title:"):
                    job["title"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("dates:"):
                    job["dates"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("- ") and "bullets" not in stripped:
                    job["bullets"].append(stripped[2:].strip())
                i += 1
            jobs.append(job)
        elif line.strip() and not line.startswith(" "):
            break
        else:
            i += 1
    return jobs, i


def _parse_yaml_skills(lines: list, i: int) -> tuple:
    """Parse skills from YAML lines."""
    skills = {}
    current_cat = None
    while i < len(lines):
        line = lines[i]
        if line.strip() and not line.startswith(" "):
            break
        stripped = line.strip()
        if stripped and not stripped.startswith("-") and stripped.endswith(":"):
            current_cat = stripped[:-1]
            skills[current_cat] = []
        elif stripped.startswith("- ") and current_cat:
            skills[current_cat].append(stripped[2:].strip())
        i += 1
    return skills, i


def _parse_yaml_projects(lines: list, i: int) -> tuple:
    """Parse projects from YAML lines."""
    projects = []
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("- name:"):
            proj = {"name": line.strip().split(":", 1)[1].strip(), "repo": "", "description": ""}
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("- name:") and lines[i].startswith("    "):
                stripped = lines[i].strip()
                if stripped.startswith("repo:"):
                    proj["repo"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("description:"):
                    proj["description"] = stripped.split(":", 1)[1].strip()
                i += 1
            projects.append(proj)
        elif line.strip() and not line.startswith(" "):
            break
        else:
            i += 1
    return projects, i


def _parse_yaml_education(lines: list, i: int) -> tuple:
    """Parse education from YAML lines."""
    entries = []
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("- institution:"):
            entry = {"institution": line.strip().split(":", 1)[1].strip()}
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("- institution:") and lines[i].startswith("    "):
                stripped = lines[i].strip()
                if stripped.startswith("degree:"):
                    entry["degree"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("location:"):
                    entry["location"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("year:"):
                    entry["year"] = stripped.split(":", 1)[1].strip()
                i += 1
            entries.append(entry)
        elif line.strip() and not line.startswith(" "):
            break
        else:
            i += 1
    return entries, i


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: master_sync.py <command>",
            "commands": ["sync", "drift", "export"],
        }))
        sys.exit(1)

    command = sys.argv[1]

    if command == "sync":
        # Parse markdown → write YAML
        md_data = parse_master_md(MASTER_MD)
        if "error" in md_data:
            print(json.dumps(md_data))
            sys.exit(1)
        write_yaml(md_data, MASTER_YAML)
        print(json.dumps({
            "status": "synced",
            "master_md": str(MASTER_MD),
            "master_yaml": str(MASTER_YAML),
            "jobs": len(md_data.get("experience", [])),
            "skill_categories": len(md_data.get("skills", {})),
            "projects": len(md_data.get("projects", [])),
            "education": len(md_data.get("education", [])),
        }))

    elif command == "drift":
        # Compare markdown vs YAML
        md_data = parse_master_md(MASTER_MD)
        if "error" in md_data:
            print(json.dumps(md_data))
            sys.exit(1)
        result = detect_drift(md_data, MASTER_YAML)
        print(json.dumps(result, indent=2))

    elif command == "export":
        # Export parsed markdown as JSON
        md_data = parse_master_md(MASTER_MD)
        print(json.dumps(md_data, indent=2))

    else:
        print(json.dumps({"error": f"Unknown command: {command}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
