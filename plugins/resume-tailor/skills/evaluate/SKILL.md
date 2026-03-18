---
name: evaluate
description: >
  Read-only resume evaluation — no modifications. Use INSTEAD OF resume-tailor when the user wants
  to understand gaps before committing to a full customization. Runs Phases 0-2 only (parse, extract,
  score, evaluate). Trigger: "evaluate my resume", "how does my resume match", "check resume fit",
  "what are the gaps", "how well do I match", "resume analysis", or when the user is deciding
  whether to run a full tailoring.
args:
  - name: resume
    description: Path to the resume file (markdown)
    required: false
  - name: job
    description: Path to job description file, URL, or pasted text
    required: false
user-invokable: true
---

# Resume Evaluator

Evaluate resume-job fit without modifying anything. This runs the analysis phases only.

## Workflow

### Step 1: Gather Inputs

Get the resume path and job description from arguments or ask the user.

### Step 2: Load Profile

```bash
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/profile_manager.py load
```

Check for existing feedback — include it in the evaluation context so the evaluator agent respects past preferences.

### Step 3: Parse & Score (parallel)

Run all three scripts in parallel:

```bash
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/parse_resume.py <resume_path>
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/extract_requirements.py <job_path>
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/ats_scorer.py --resume <resume_path> --job <job_path>
```

### Step 4: Evaluate

Spawn the resume-evaluator agent with parsed data, requirements, ATS score, and any stored feedback.

```
Agent(
  subagent_type="resume-tailor:resume-evaluator",
  description="Evaluate resume-job fit",
  prompt="<include parsed resume, requirements, ATS score, feedback>"
)
```

### Step 5: Present Results

Show the user:
- Overall match score
- Top strengths and gaps
- Term mismatches
- Section-by-section scores
- Recommendations for improvement

Ask if they'd like to proceed with full customization (`/resume-tailor`).

## Shared Scripts

All scripts live in `${PLUGIN_ROOT}/skills/resume-tailor/scripts/` — shared with the main resume-tailor skill.
