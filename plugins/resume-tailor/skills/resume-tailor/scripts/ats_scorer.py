#!/usr/bin/env python3
"""
ABOUTME: Calculates an ATS (Applicant Tracking System) match score between a resume and job description.
ABOUTME: Outputs JSON with overall score, matched/missing keywords, and section-weighted analysis.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


# Section weights for ATS scoring
SECTION_WEIGHTS = {
    "skills": 0.40,
    "experience": 0.30,
    "education": 0.20,
    "summary": 0.10,
}

# Stop words for keyword extraction
STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "must", "this", "that", "these", "those", "it", "its", "we", "our",
    "you", "your", "they", "their", "not", "no", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "than", "too",
    "very", "just", "about", "also", "any", "here", "into", "only", "so",
    "then", "there", "through", "up", "out", "if", "while", "well",
})


def tokenize(text: str) -> list:
    """Extract meaningful tokens from text."""
    # Preserve multi-word technical terms
    text_lower = text.lower()
    tokens = re.findall(r"\b[a-z][a-z+#./\-]{1,}\b", text_lower)
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


def extract_bigrams(tokens: list) -> list:
    """Extract word pairs that might represent compound skills."""
    bigrams = []
    for i in range(len(tokens) - 1):
        bigrams.append(f"{tokens[i]} {tokens[i + 1]}")
    return bigrams


def extract_job_keywords(job_text: str) -> dict:
    """Extract and score keywords from job description."""
    tokens = tokenize(job_text)
    bigrams = extract_bigrams(tokens)

    # Count frequencies
    token_counts = Counter(tokens)
    bigram_counts = Counter(bigrams)

    # Combine: high-frequency unigrams + meaningful bigrams
    keywords = {}

    # Unigrams appearing 2+ times are likely important
    for token, count in token_counts.items():
        if count >= 2:
            keywords[token] = count

    # Bigrams appearing 2+ times (compound terms)
    for bigram, count in bigram_counts.items():
        if count >= 2:
            keywords[bigram] = count

    # Always include single-occurrence technical terms
    tech_patterns = [
        r"python|java|javascript|typescript|rust|golang|ruby|swift|kotlin|scala|php",
        r"react|angular|vue|node|django|flask|fastapi|spring|rails|next",
        r"aws|azure|gcp|kubernetes|docker|terraform|ansible",
        r"postgres|mysql|mongodb|redis|elasticsearch|dynamodb|sqlite|cassandra",
        r"machine\s*learning|deep\s*learning|nlp|data\s*science",
        r"git|agile|scrum|tdd|rest|graphql|microservices?|oauth|jwt",
        r"ci/cd|devops|sre|infrastructure",
    ]
    combined_pattern = "|".join(tech_patterns)
    tech_matches = re.findall(combined_pattern, job_text.lower())
    for match in tech_matches:
        keywords[match] = keywords.get(match, 0) + 3  # Boost technical terms

    return keywords


def parse_resume_sections(resume_text: str) -> dict:
    """Quick section parser for the resume (lightweight version)."""
    sections = {}
    current_section = "header"
    current_lines = []

    # Only split on ## (h2) headings — h3 headings are entries within sections
    heading_re = re.compile(r"^##\s+(.+)$")

    section_map = {
        "summary": "summary", "professional summary": "summary", "about": "summary",
        "profile": "summary", "objective": "summary",
        "experience": "experience", "work experience": "experience",
        "professional experience": "experience", "work history": "experience",
        "skills": "skills", "technical skills": "skills", "competencies": "skills",
        "core competencies": "skills", "technologies": "skills",
        "education": "education", "certifications": "education",
        "projects": "projects", "publications": "publications",
    }

    for line in resume_text.split("\n"):
        match = heading_re.match(line)
        if match:
            # Save previous section
            sections[current_section] = "\n".join(current_lines)
            heading = match.group(1).strip().lower()
            current_section = section_map.get(heading, "other")
            current_lines = []
        else:
            current_lines.append(line)

    sections[current_section] = "\n".join(current_lines)
    return sections


def calculate_section_score(section_text: str, job_keywords: dict) -> dict:
    """Calculate how well a resume section matches job keywords."""
    section_lower = section_text.lower()
    section_tokens = set(tokenize(section_text))
    section_bigrams = set(extract_bigrams(list(section_tokens)))
    section_all = section_tokens | section_bigrams

    matched = []
    missing = []

    for keyword, importance in sorted(job_keywords.items(), key=lambda x: -x[1]):
        # Check both exact token match and substring match
        if keyword in section_all or keyword in section_lower:
            matched.append(keyword)
        else:
            missing.append(keyword)

    total = len(job_keywords)
    match_count = len(matched)
    score = round(match_count / total * 100, 1) if total > 0 else 0

    return {
        "score": score,
        "matched": matched[:20],  # Top 20 matches
        "missing": missing[:20],  # Top 20 misses
        "matched_count": match_count,
        "total_keywords": total,
    }


def calculate_keyword_density(resume_text: str, job_keywords: dict) -> float:
    """Calculate overall keyword density in the resume."""
    resume_lower = resume_text.lower()
    resume_tokens = tokenize(resume_text)
    total_tokens = len(resume_tokens)
    if total_tokens == 0:
        return 0.0

    keyword_occurrences = 0
    for keyword in job_keywords:
        keyword_occurrences += resume_lower.count(keyword)

    return round(keyword_occurrences / total_tokens * 100, 2)


def score_resume(resume_path: str, job_path: str) -> dict:
    """Calculate the full ATS match score."""
    resume_file = Path(resume_path).expanduser()
    job_file = Path(job_path).expanduser()

    if not resume_file.exists():
        return {"error": f"Resume file not found: {resume_path}"}
    if not job_file.exists():
        return {"error": f"Job description file not found: {job_path}"}

    resume_text = resume_file.read_text(encoding="utf-8")
    job_text = job_file.read_text(encoding="utf-8")

    # Extract job keywords
    job_keywords = extract_job_keywords(job_text)

    # Parse resume sections
    resume_sections = parse_resume_sections(resume_text)

    # Score each section
    section_scores = {}
    weighted_total = 0.0
    weight_sum = 0.0

    for section_type, weight in SECTION_WEIGHTS.items():
        section_text = resume_sections.get(section_type, "")
        if section_text.strip():
            score_data = calculate_section_score(section_text, job_keywords)
            section_scores[section_type] = {
                "weight": weight,
                "score": score_data["score"],
                "weighted_score": round(score_data["score"] * weight, 1),
                "matched": score_data["matched"],
                "missing": score_data["missing"],
            }
            weighted_total += score_data["score"] * weight
            weight_sum += weight
        else:
            section_scores[section_type] = {
                "weight": weight,
                "score": 0,
                "weighted_score": 0,
                "matched": [],
                "missing": list(job_keywords.keys())[:10],
                "note": "Section not found in resume",
            }
            weight_sum += weight

    # Normalize if not all sections present
    overall_score = round(weighted_total / weight_sum, 1) if weight_sum > 0 else 0

    # Overall keyword analysis
    all_matched = set()
    all_missing = set()
    for ss in section_scores.values():
        all_matched.update(ss.get("matched", []))
        all_missing.update(ss.get("missing", []))
    # Remove from missing if found in any section
    all_missing -= all_matched

    density = calculate_keyword_density(resume_text, job_keywords)

    result = {
        "overall_score": overall_score,
        "section_scores": section_scores,
        "keyword_density": density,
        "total_job_keywords": len(job_keywords),
        "matched_keywords": sorted(all_matched)[:30],
        "missing_keywords": sorted(all_missing)[:30],
        "score_interpretation": interpret_score(overall_score),
    }
    return result


def interpret_score(score: float) -> str:
    """Provide human-readable interpretation of the ATS score."""
    if score >= 80:
        return "Excellent match — resume is well-aligned with job requirements"
    elif score >= 65:
        return "Good match — minor keyword gaps could be addressed"
    elif score >= 50:
        return "Moderate match — notable gaps in keyword coverage"
    elif score >= 35:
        return "Weak match — significant keyword gaps need attention"
    else:
        return "Poor match — major alignment issues between resume and job"


def main():
    parser = argparse.ArgumentParser(description="Calculate ATS match score")
    parser.add_argument("--resume", required=True, help="Path to resume markdown file")
    parser.add_argument("--job", required=True, help="Path to job description file")
    args = parser.parse_args()

    result = score_resume(args.resume, args.job)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
