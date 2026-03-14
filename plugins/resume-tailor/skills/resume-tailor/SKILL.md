---
name: resume-tailor
description: >
  Customize a resume and optionally generate a cover letter for a specific job description.
  Use when the user wants to tailor, customize, optimize, or adapt their resume for a job posting.
  Trigger phrases include "tailor my resume", "customize my resume", "optimize my resume for this job",
  "adapt my resume", "match my resume to this job", "ATS optimize", "resume for this position",
  "help me apply", "write a cover letter", "cover letter for this job", "resume customization",
  "job application", and "make my resume match this job". This skill runs a multi-agent pipeline:
  deterministic scripts parse and score, specialized agents evaluate and optimize sections in parallel,
  and a truthfulness verifier ensures no fabrication.
args:
  - name: resume
    description: Path to the resume file (markdown). If omitted, checks profile for last known path.
    required: false
  - name: job
    description: Path to job description file, or the job description text/URL
    required: false
user-invokable: true
---

# Resume Tailor

## Overview

This skill orchestrates a 7-phase pipeline to customize a resume for a specific job description. It combines deterministic Python scripts (parsing, scoring, diffing) with specialized LLM agents (evaluation, optimization, verification) for fast, accurate resume tailoring.

The key architectural win: section optimization runs **in parallel** — one agent per section, all spawned simultaneously.

## Prerequisites

- A resume in **markdown format** (.md file)
- A job description (file path, pasted text, or URL)
- Python 3.10+ available (for running scripts)

## Phase 0: Profile Load & Enrich

### Load User Profile

Run the profile manager to check for existing user data:

```bash
python ${SKILL_DIR}/scripts/profile_manager.py load
```

This returns:
- Existing profile data (name, career level, preferences)
- Recent customization history
- Cached enrichment data (GitHub, portfolio)
- Whether this is a new user

### Gather Inputs

If `resume` argument is provided, use that path. Otherwise:
1. Check the loaded profile for `resume_path`
2. Ask the user for their resume file path

If `job` argument is provided, use that. Otherwise:
1. Ask the user for the job description (file path, URL, or pasted text)
2. If a URL is provided, use WebFetch to retrieve the content and save to a temp file

### Handle Job Description Input

- **File path**: Use directly
- **URL**: Fetch with WebFetch, save content to `/tmp/job_description.txt`
- **Pasted text**: Save to `/tmp/job_description.txt`

### Optional: GitHub Enrichment

If the resume contains a GitHub URL or the user provides a GitHub username:

```bash
python ${SKILL_DIR}/scripts/enrich_github.py --username <github_username>
```

This caches results and provides skill corroboration data.

### Load Preferences

From the profile, check:
- `aggressiveness`: conservative / balanced / extensive (default: balanced)
- `cover_letter`: always / ask / never (default: ask)
- `preserve_sections`: sections to never modify (e.g., contact info)

## Phase 1: Gather & Parse

Run all three deterministic scripts. These are independent and can be run in parallel:

```bash
# Parse the resume into structured sections
python ${SKILL_DIR}/scripts/parse_resume.py <resume_path>

# Extract requirements from the job description
python ${SKILL_DIR}/scripts/extract_requirements.py <job_path>

# Calculate initial ATS match score
python ${SKILL_DIR}/scripts/ats_scorer.py --resume <resume_path> --job <job_path>
```

Store the JSON outputs — they feed into the next phases.

**Present to user**: "Your resume has [N] sections and [M] words. Initial ATS match score: **[score]/100** — [interpretation]."

## Phase 2: Evaluate

Spawn the **resume-evaluator** agent as a subagent:

```
Agent(
  subagent_type="resume-tailor:resume-evaluator",
  description="Evaluate resume-job fit",
  prompt="Evaluate the fit between this resume and job description.

PARSED RESUME:
<paste parse_resume.py JSON output>

EXTRACTED REQUIREMENTS:
<paste extract_requirements.py JSON output>

INITIAL ATS SCORE:
<paste ats_scorer.py JSON output>

ENRICHMENT DATA (if available):
<paste GitHub/portfolio enrichment data>

PROFILE HISTORY (if returning user):
<paste recent customization history>

Read references/resume-best-practices.md for formatting standards.
Return your evaluation as a structured JSON assessment."
)
```

The evaluator returns:
- Overall match score
- Section-by-section evaluation with priorities
- Gap analysis and term mismatches
- Industry classification
- Optimization priority order

**Present to user**: Brief summary of match score, top strengths, and top gaps.

## Phase 3: Optimize Sections (PARALLEL)

This is the key performance phase. For each resume section that needs optimization (based on evaluator's priority), spawn a **section-optimizer** agent. **Spawn ALL of them in a single message for parallel execution.**

Example for a 5-section resume:

```
# In ONE message, spawn all section optimizers:

Agent(
  subagent_type="resume-tailor:section-optimizer",
  description="Optimize summary section",
  prompt="Optimize the SUMMARY section of this resume for the target job.

ORIGINAL SECTION:
<paste summary section content>

JOB REQUIREMENTS (relevant to this section):
<paste relevant requirements>

EVALUATION FINDINGS:
<paste evaluator's summary section assessment>

CAREER LEVEL: <from evaluation>
INDUSTRY: <from evaluation>

Read references/action-verbs.md for verb guidance.
Read references/industry-conventions.md for industry standards.
Return optimized section text + list of changes with rationale."
)

Agent(
  subagent_type="resume-tailor:section-optimizer",
  description="Optimize experience section",
  prompt="Optimize the EXPERIENCE section..."
)

Agent(
  subagent_type="resume-tailor:section-optimizer",
  description="Optimize skills section",
  prompt="Optimize the SKILLS section..."
)

# ... one agent per section
```

### Sections to Skip

- Sections marked as "preserve" in user preferences
- Contact information (never modify)
- Sections the evaluator scored >90 relevance (already strong)

### Handling Optimizer Results

Collect all optimized sections. If any optimizer returns unclear results, the main agent can directly handle minor adjustments.

## Phase 4: Verify

Spawn the **truthfulness-verifier** agent. This agent has NOT seen the optimization prompts — it receives only original vs. optimized content.

```
Agent(
  subagent_type="resume-tailor:truthfulness-verifier",
  description="Verify truthfulness",
  prompt="Compare the original and optimized resume sections for fabrication.

ORIGINAL RESUME:
<paste full original resume text>

OPTIMIZED SECTIONS:
<paste all optimized section texts>

Check for:
- Added skills not in the original
- Fabricated metrics or numbers
- Changed company names, titles, or dates
- Invented credentials or certifications
- Removed experience entries

Return PASS/FAIL with specific issues."
)
```

### If Verification FAILS

1. Review the specific issues reported
2. For minor issues (e.g., inferred metric): fix directly in the assembled resume
3. For major issues (e.g., added skills): re-spawn the section-optimizer for affected sections with explicit correction instructions
4. Re-verify after fixes

### If Verification PASSES

Proceed to cover letter (if requested) and assembly.

## Phase 5: Cover Letter (Optional)

Check user preferences:
- If `cover_letter: always` → generate automatically
- If `cover_letter: ask` → ask the user "Would you like a cover letter?"
- If `cover_letter: never` → skip

If generating:

```
Agent(
  subagent_type="resume-tailor:cover-letter-writer",
  description="Write cover letter",
  prompt="Write a tailored cover letter.

OPTIMIZED RESUME:
<paste final optimized resume>

JOB DESCRIPTION:
<paste full job description>

INDUSTRY: <from evaluation>
COMPANY: <from requirements extraction>
CANDIDATE NAME: <from resume header>

Read references/cover-letter-guide.md for structure and tone guidance.
Read references/industry-conventions.md for industry tone.
Return a 250-400 word cover letter in markdown."
)
```

## Phase 6: Assemble & Report

### Assemble the Optimized Resume

1. Reconstruct the full resume from optimized sections + unchanged sections
2. Preserve the original header/contact information
3. Maintain consistent markdown formatting

### Write Output Files

Determine output filenames:
- Resume: `<original_name>_customized.md` (same directory as original)
- Cover letter: `cover_letter_<company_slug>.md` (same directory)

Write both files using the Write tool.

### Calculate After Score

```bash
python ${SKILL_DIR}/scripts/ats_scorer.py --resume <optimized_path> --job <job_path>
```

### Generate Change Report

```bash
python ${SKILL_DIR}/scripts/diff_report.py --original <original_path> --optimized <optimized_path>
```

### Save History

```bash
echo '{"job_title": "<title>", "company": "<company>", "resume_used": "<path>", "ats_score_before": <before>, "ats_score_after": <after>, "sections_modified": [<sections>], "cover_letter_generated": <bool>, "output_files": {"resume": "<path>", "cover_letter": "<path>"}}' | python ${SKILL_DIR}/scripts/profile_manager.py save-history
```

### Present Results to User

Show:
1. **Files created**: paths to customized resume and cover letter
2. **ATS Score**: Before → After (with delta)
3. **Change summary**: Which sections were modified and why
4. **Key improvements**: Top 3-5 changes made

Format:
```
## Resume Customization Complete

**Target**: [Job Title] at [Company]

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| ATS Score | [X] | [Y] | +[Z] |

**Files created:**
- Resume: `[path]`
- Cover letter: `[path]`

**Key changes:**
1. [Change 1]
2. [Change 2]
3. [Change 3]

**Change report:**
[Include diff report output]
```

## Edge Cases

### No Resume File Provided
Ask the user for the path. Check common locations: `~/resume.md`, `~/Documents/resume.md`.

### Job Description is a URL
Use WebFetch to retrieve the page content. Extract the job posting text. Save to temp file.

### Resume Has Unusual Sections
The parser classifies unknown sections as "other". The evaluator will assess relevance. The optimizer will handle them generically.

### Very Short Resume (< 200 words)
Warn the user that the resume may be too brief. Suggest adding more detail before optimization.

### Career Change Resume
The evaluator will detect a mismatch between resume industry and job industry. Section optimizers should emphasize transferable skills and reframe experience in the target industry's language.

### Verification Fails Repeatedly
If verification fails 2+ times on the same section, flag it for the user's manual review rather than re-optimizing indefinitely.

## Script Reference

| Script | Input | Output |
|--------|-------|--------|
| `parse_resume.py <file>` | Resume markdown | JSON: sections, metadata, contact |
| `extract_requirements.py <file>` | Job description | JSON: title, skills, keywords |
| `ats_scorer.py --resume <r> --job <j>` | Both files | JSON: score, matched/missing |
| `diff_report.py --original <o> --optimized <n>` | Both files | Markdown change report |
| `profile_manager.py load` | None | JSON: profile, preferences, history |
| `profile_manager.py save-history` | JSON stdin | Saves history record |
| `enrich_github.py --username <u>` | GitHub user | JSON: repos, languages, activity |
