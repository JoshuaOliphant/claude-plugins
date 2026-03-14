#!/usr/bin/env python3
"""
ABOUTME: Extracts structured requirements, skills, and keywords from a job description.
ABOUTME: Outputs JSON with title, company, skills, experience level, and keyword frequency.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path


# Common stop words to exclude from keyword analysis
STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "must", "this", "that", "these", "those", "it", "its", "we", "our",
    "you", "your", "they", "their", "he", "she", "his", "her", "who",
    "which", "what", "where", "when", "how", "not", "no", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such",
    "than", "too", "very", "just", "about", "above", "after", "again",
    "also", "any", "because", "before", "between", "during", "here",
    "into", "only", "over", "own", "same", "so", "then", "there",
    "through", "under", "up", "out", "if", "while", "including",
    "within", "across", "well", "etc", "strong", "ability", "work",
    "working", "looking", "join", "team", "role", "position", "company",
    "opportunity", "responsibilities", "requirements", "qualifications",
    "required", "preferred", "nice", "plus", "bonus", "ideal",
    "candidate", "applicant", "apply", "application", "submit",
    "resume", "cover", "letter", "salary", "benefits", "equal",
    "employer", "employment", "offer",
})

# Patterns for detecting experience level
EXPERIENCE_PATTERNS = {
    "entry": [
        r"entry[\s-]?level", r"junior", r"0[\s-]?[12]\s*years?",
        r"new\s+grad", r"recent\s+graduate", r"internship",
    ],
    "mid": [
        r"mid[\s-]?level", r"[23456]\+?\s*years?", r"intermediate",
    ],
    "senior": [
        r"senior", r"sr\.", r"[789]\+?\s*years?", r"1[0-9]\+?\s*years?",
        r"lead", r"principal", r"staff",
    ],
    "executive": [
        r"executive", r"director", r"vp\b", r"vice\s+president",
        r"c[\s-]?level", r"chief", r"head\s+of", r"15\+?\s*years?",
        r"20\+?\s*years?",
    ],
}

# Common technical skills and their variations
TECH_SKILL_PATTERNS = [
    # Languages
    r"\bpython\b", r"\bjava(?:script)?\b", r"\btypescript\b", r"\brust\b",
    r"\bgo(?:lang)?\b", r"\bc\+\+\b", r"\bc#\b", r"\bruby\b", r"\bswift\b",
    r"\bkotlin\b", r"\bscala\b", r"\bphp\b", r"\br\b(?=\s|,|/)",
    # Frameworks
    r"\breact\b", r"\bangular\b", r"\bvue\.?js?\b", r"\bnode\.?js?\b",
    r"\bdjango\b", r"\bflask\b", r"\bfastapi\b", r"\bspring\b",
    r"\brails\b", r"\b\.net\b", r"\bnext\.?js?\b",
    # Cloud & infra
    r"\baws\b", r"\bazure\b", r"\bgcp\b", r"\bgoogle\s+cloud\b",
    r"\bkubernetes\b", r"\bk8s\b", r"\bdocker\b", r"\bterraform\b",
    r"\bansible\b", r"\bci/?cd\b", r"\bcontinuous\s+(integration|deployment|delivery)\b",
    # Databases
    r"\bpostgres(?:ql)?\b", r"\bmysql\b", r"\bmongodb\b", r"\bredis\b",
    r"\belasticsearch\b", r"\bdynamodb\b", r"\bsql\b", r"\bnosql\b",
    r"\bsqlite\b", r"\bcassandra\b",
    # Data & ML
    r"\bmachine\s+learning\b", r"\bml\b", r"\bdeep\s+learning\b",
    r"\bai\b", r"\bartificial\s+intelligence\b", r"\bnlp\b",
    r"\bdata\s+science\b", r"\bpandas\b", r"\bnumpy\b",
    r"\btensorflow\b", r"\bpytorch\b", r"\bscikit[\s-]learn\b",
    # Tools & practices
    r"\bgit\b", r"\bjira\b", r"\bagile\b", r"\bscrum\b",
    r"\btdd\b", r"\brest(?:ful)?\b", r"\bgraphql\b", r"\bmicroservices?\b",
    r"\bapi\b", r"\boauth\b", r"\bjwt\b",
]


def detect_experience_level(text: str) -> str:
    """Detect the required experience level from job description."""
    text_lower = text.lower()
    scores = {}
    for level, patterns in EXPERIENCE_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, text_lower))
        if score > 0:
            scores[level] = score

    if not scores:
        return "unknown"
    return max(scores, key=scores.get)


def extract_title(text: str) -> str:
    """Extract the job title from the description."""
    lines = text.strip().split("\n")
    # First non-empty line is often the title
    for line in lines[:5]:
        stripped = line.strip()
        # Skip lines that look like company names, locations, or labels
        if stripped and len(stripped) < 100:
            cleaned = re.sub(r"^#+\s*", "", stripped)
            cleaned = re.sub(r"^(job\s+title|position|role)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
            if cleaned and not re.match(r"^(about|company|location|department|posted)", cleaned, re.IGNORECASE):
                return cleaned
    return "Unknown Position"


def extract_company(text: str) -> str:
    """Try to extract company name from the job description."""
    # Look for "at Company", "Company is", "About Company" patterns
    patterns = [
        r"(?:at|@)\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s*[,\-\n])",
        r"(?:about|join)\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s*[,\-\n!.])",
        r"(?:company|employer)\s*:\s*(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            company = match.group(1).strip()
            if len(company) < 50:
                return company
    return "Unknown Company"


def extract_skills(text: str) -> list:
    """Extract technical skills mentioned in the description."""
    text_lower = text.lower()
    found = []
    for pattern in TECH_SKILL_PATTERNS:
        matches = re.findall(pattern, text_lower)
        if matches:
            # Get the original case version from text
            original_match = re.search(pattern, text, re.IGNORECASE)
            if original_match:
                skill = original_match.group().strip()
                if skill not in found:
                    found.append(skill)
    return found


def extract_keywords(text: str, top_n: int = 30) -> list:
    """Extract top keywords by frequency, excluding stop words."""
    # Tokenize: split on non-alphanumeric characters
    words = re.findall(r"\b[a-zA-Z][a-zA-Z+#.]{1,}\b", text)
    filtered = [w.lower() for w in words if w.lower() not in STOP_WORDS and len(w) > 2]
    counts = Counter(filtered)
    return [{"keyword": kw, "count": count} for kw, count in counts.most_common(top_n)]


def extract_requirements_sections(text: str) -> dict:
    """Split job description into requirement categories."""
    sections = {
        "required": [],
        "preferred": [],
        "responsibilities": [],
        "benefits": [],
    }

    current_section = None
    lines = text.split("\n")

    for line in lines:
        stripped = line.strip().lower()

        # Detect section headers
        if re.search(r"(required|must[\s-]have|minimum|essential)", stripped):
            current_section = "required"
            continue
        elif re.search(r"(preferred|nice[\s-]to[\s-]have|bonus|desired|ideal)", stripped):
            current_section = "preferred"
            continue
        elif re.search(r"(responsibilit|duties|what\s+you.ll\s+do|day[\s-]to[\s-]day)", stripped):
            current_section = "responsibilities"
            continue
        elif re.search(r"(benefit|perk|we\s+offer|compensation|what\s+we\s+offer)", stripped):
            current_section = "benefits"
            continue

        # Extract bullet items
        if current_section and re.match(r"\s*[-*•]\s+", line):
            item = re.sub(r"^\s*[-*•]\s+", "", line).strip()
            if item:
                sections[current_section].append(item)

    return sections


def extract_requirements(filepath: str) -> dict:
    """Extract structured requirements from a job description file."""
    path = Path(filepath).expanduser()
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    text = path.read_text(encoding="utf-8")

    title = extract_title(text)
    company = extract_company(text)
    skills = extract_skills(text)
    keywords = extract_keywords(text)
    level = detect_experience_level(text)
    req_sections = extract_requirements_sections(text)

    # Years of experience extraction
    years_match = re.search(r"(\d+)\+?\s*years?", text, re.IGNORECASE)
    years_experience = int(years_match.group(1)) if years_match else None

    result = {
        "file": str(path),
        "title": title,
        "company": company,
        "experience_level": level,
        "years_experience": years_experience,
        "skills": skills,
        "keywords": keywords,
        "sections": req_sections,
        "metadata": {
            "total_requirements": len(req_sections["required"]),
            "total_preferred": len(req_sections["preferred"]),
            "total_responsibilities": len(req_sections["responsibilities"]),
            "word_count": len(text.split()),
        },
    }
    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: extract_requirements.py <job_description.txt>"}))
        sys.exit(1)

    result = extract_requirements(sys.argv[1])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
