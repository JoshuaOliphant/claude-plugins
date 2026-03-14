---
name: ats-score
description: >
  Quick ATS score check between a resume and job description. No agents, no optimization —
  just the deterministic scoring scripts. Use when the user wants a fast score check, wants
  to compare before/after, or wants to iterate on their resume manually. Trigger phrases
  include "ATS score", "check my score", "how does my resume score", "keyword match",
  "score check", "quick score", and "ATS check".
args:
  - name: resume
    description: Path to the resume file (markdown)
    required: true
  - name: job
    description: Path to job description file
    required: true
user-invokable: true
---

# ATS Score Check

Fast, deterministic ATS scoring — no agents, no LLM calls. Just the scripts.

## Workflow

### Step 1: Run Scripts

```bash
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/parse_resume.py <resume_path>
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/ats_scorer.py --resume <resume_path> --job <job_path>
```

### Step 2: Present Results

Show the user:

| Section | Score | Matched | Missing (top 5) |
|---------|-------|---------|-----------------|
| Skills | X | N keywords | keyword1, keyword2, ... |
| Experience | X | N keywords | ... |
| Education | X | N keywords | ... |
| Summary | X | N keywords | ... |
| **Overall** | **X** | | |

**Keyword density**: X%

**Top missing keywords**: list the most impactful missing keywords

### Step 3: Suggest Next Steps

Based on the score:
- Score >= 65: "Good match — minor tweaks could help. Run `/resume-tailor` for full optimization."
- Score 35-64: "Moderate match — there are clear gaps. Run `/resume-tailor:evaluate` for detailed analysis."
- Score < 35: "Significant gaps — recommend full `/resume-tailor` pipeline."
