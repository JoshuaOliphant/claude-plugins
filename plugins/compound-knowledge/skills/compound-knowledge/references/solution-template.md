# ABOUTME: Template for new solution files in knowledge/solutions/
# ABOUTME: Used by the compound-knowledge skill when capturing solved problems

# Solution File Template

Use this template when creating new solution files. Replace placeholders with actual content.

```markdown
---
title: "{Clear problem title}"
project: {project-name}
date: {YYYY-MM-DD}
problem_type: {enum value from yaml-schema.md}
component: {enum value from yaml-schema.md}
symptoms:
  - "{Observable symptom or error message 1}"
  - "{Observable symptom or error message 2}"
solution_summary: "{One-line summary of what fixed it}"
severity: {critical|high|medium|low}
root_cause: {enum value from yaml-schema.md}
resolution_type: {enum value from yaml-schema.md}
tags: [{keyword1}, {keyword2}, {keyword3}]
environment: "{Runtime context if relevant}"
related_solutions:
  - "{category}/{related-file}.md"
---

## Problem

{2-3 sentences describing the problem. What were you trying to do? What went wrong?}

## Environment

- **Project**: {project name}
- **Stack**: {relevant technologies and versions}
- **Context**: {what circumstances led to this problem}

## Symptoms

{List observable symptoms — error messages, unexpected behavior, failed tests}

- {Symptom 1 with exact error message if available}
- {Symptom 2}

## What Didn't Work

{Document failed attempts — this is valuable for future searchers who might try the same things}

1. **{Failed approach 1}**: {Why it didn't work}
2. **{Failed approach 2}**: {Why it didn't work}

## Solution

{Describe the fix clearly. Include enough detail that someone else could apply it.}

### Implementation

{Code examples showing the fix}

```{language}
{code example}
```

### Why This Works

{1-2 sentences explaining WHY this solution addresses the root cause}

## Prevention

{How to avoid this problem in the future}

- {Prevention strategy 1}
- {Prevention strategy 2}

## Related

- {Link to related solution files}
- {Link to relevant documentation}
- {Project or reflection references}
```

## Guidelines for Using This Template

1. **Symptoms are key** — future searchers will grep by symptoms. Include exact error messages.
2. **Failed attempts matter** — "What Didn't Work" saves others from repeating mistakes.
3. **Code examples required** — if the solution involves code, show it.
4. **Keep it focused** — one problem per file. If you solved multiple issues, create multiple files.
5. **Cross-reference** — link to related solutions via `related_solutions` frontmatter field.
