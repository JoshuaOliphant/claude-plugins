---
name: cover-letter
description: >
  Cover letter only — no resume optimization. Use INSTEAD OF resume-tailor when the user already
  has a tailored resume and just needs a cover letter, or explicitly asks for "just the cover letter".
  Trigger: "write a cover letter", "cover letter for this job", "I need a cover letter", "draft a
  cover letter", "cover letter only". Uses existing (or previously customized) resume as context.
args:
  - name: resume
    description: Path to the resume file (markdown). Uses customized version if available.
    required: false
  - name: job
    description: Path to job description file, URL, or pasted text
    required: false
  - name: company
    description: Company name (extracted automatically if not provided)
    required: false
user-invokable: true
---

# Cover Letter Generator

Generate a standalone cover letter without running the full resume optimization pipeline.

## Workflow

### Step 1: Gather Inputs

Get the resume path, job description, and optional company name.

If no resume is provided, check the profile for the last customized resume path.

### Step 2: Load Context

```bash
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/profile_manager.py load
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/extract_requirements.py <job_path>
```

Load any stored feedback relevant to cover letters.

### Step 3: Read Resume

Read the resume file to provide context for the cover letter writer.

### Step 4: Generate Cover Letter

Spawn the cover-letter-writer agent:

```
Agent(
  subagent_type="resume-tailor:cover-letter-writer",
  description="Write cover letter",
  prompt="Write a tailored cover letter.

RESUME:
<paste resume content>

JOB DESCRIPTION:
<paste job description>

INDUSTRY: <detected or provided>
COMPANY: <from extraction or argument>
CANDIDATE NAME: <from resume>

STORED FEEDBACK (apply these preferences):
<paste any cover letter feedback>

Read references/cover-letter-guide.md for structure and tone guidance.
Read references/industry-conventions.md for industry tone.
Return a 250-400 word cover letter in markdown."
)
```

### Step 5: Write & Present

Write the cover letter to a file alongside the resume. Present it to the user.

Ask: "Would you like me to adjust the tone, length, or focus?"

If the user provides feedback, save it:
```bash
echo '{"category": "cover_letter", "feedback": "<user feedback>"}' | \
  python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/profile_manager.py save-feedback
```

## Shared Resources

- Scripts: `${PLUGIN_ROOT}/skills/resume-tailor/scripts/`
- References: `${PLUGIN_ROOT}/skills/resume-tailor/references/`
- Agent: `resume-tailor:cover-letter-writer`
