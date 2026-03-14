---
name: feedback
description: >
  Save, view, or manage feedback about resume customization preferences. Feedback persists
  across sessions and is automatically loaded by the resume-tailor pipeline to guide future
  optimizations. Use when the user wants to save resume preferences, give feedback on output,
  set rules for future customizations, or review stored feedback. Trigger phrases include
  "remember this for next time", "save this feedback", "don't do that again",
  "always do this", "show my feedback", "resume preferences", "clear feedback",
  "what feedback have I given", and "remember for future resumes".
args:
  - name: action
    description: "Action to take: save, show, or clear"
    required: false
user-invokable: true
---

# Resume Feedback Manager

Persist resume customization feedback across sessions. Stored feedback is automatically loaded
during Phase 0 of the resume-tailor pipeline and passed to all agents.

## Actions

### Save Feedback

When the user provides feedback on a customization result, save it:

```bash
echo '{"category": "<section_or_general>", "feedback": "<what the user said>", "context": "<optional job/company>"}' | \
  python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/profile_manager.py save-feedback
```

**Categories**: summary, experience, skills, education, projects, cover_letter, formatting, general, tone

**Examples**:
- "Don't change my summary tone" → `{"category": "summary", "feedback": "Preserve the original conversational tone — do not make it more formal"}`
- "Always emphasize Kubernetes" → `{"category": "skills", "feedback": "Kubernetes experience should always be prominently featured regardless of job requirements"}`
- "Keep my projects section short" → `{"category": "projects", "feedback": "Limit projects section to 3 bullets maximum"}`
- "I prefer active voice in cover letters" → `{"category": "cover_letter", "feedback": "Use active voice throughout, avoid passive constructions"}`

### Show Feedback

Display all stored feedback:

```bash
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/profile_manager.py show-feedback
```

Present as a readable list grouped by category.

### Clear Feedback

Clear all feedback or feedback for a specific category:

```bash
# Clear all
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/profile_manager.py clear-feedback

# Clear only cover letter feedback
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/profile_manager.py clear-feedback cover_letter
```

## How Feedback is Used

When the resume-tailor pipeline runs, it loads all feedback entries during Phase 0 and includes
them in the prompts for relevant agents:

- **Summary feedback** → passed to the summary section-optimizer
- **Experience feedback** → passed to the experience section-optimizer
- **Cover letter feedback** → passed to the cover-letter-writer agent
- **General/formatting feedback** → passed to all agents
- **Tone feedback** → passed to all writing agents

This ensures the user never has to repeat the same correction twice.
