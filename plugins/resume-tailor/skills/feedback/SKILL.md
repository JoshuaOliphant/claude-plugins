---
name: feedback
description: >
  Save resume customization feedback proactively. MUST trigger when the user corrects resume output
  ("don't do that again", "always do this", "wrong tone", "too many bullet points") or confirms
  good output ("perfect", "yes like that"). Also trigger on explicit requests: "save this feedback",
  "show my feedback", "clear feedback", "resume preferences", "consolidate feedback", "bake in my
  preferences". Feedback loaded automatically by the resume-tailor pipeline across sessions.
args:
  - name: action
    description: "Action to take: save, show, clear, or consolidate"
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

### Consolidate Feedback

Graduate stable feedback into the actual SKILL.md files, making corrections permanent. This is a
Claude-driven operation — no script needed.

**When to consolidate**: When the user says "update the plugin based on feedback", "consolidate feedback",
"bake in my preferences", or "graduate feedback into the skill".

**Process**:

1. Load all stored feedback:
```bash
python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/profile_manager.py show-feedback
```

2. Read the target SKILL.md file:
   - `${PLUGIN_ROOT}/skills/resume-tailor/SKILL.md`

3. For each feedback entry, determine if it should be consolidated:
   - **Consolidate**: Universal preferences, repeated corrections, style rules that always apply
   - **Keep as runtime feedback**: Situational preferences, context-dependent corrections, temporary focus areas

4. Present a consolidation plan to the user:
   ```
   ## Consolidation Plan

   **Will bake into SKILL.md** (permanent):
   - [feedback] → edit [file]: [what will change]

   **Will keep as runtime feedback** (situational):
   - [feedback] → reason: [why it stays runtime]

   Proceed?
   ```

5. On approval:
   - Edit the target SKILL.md files using the Edit tool
   - Clear only the graduated feedback entries:
   ```bash
   python ${PLUGIN_ROOT}/skills/resume-tailor/scripts/profile_manager.py clear-feedback <category>
   ```
   - Keep non-graduated entries untouched

6. Report what changed and what remains as runtime feedback.

## How Feedback is Used

When the resume-tailor pipeline runs, it loads all feedback entries during Phase 0 and includes
them in the prompts for relevant agents:

- **Summary feedback** → passed to the summary section-optimizer
- **Experience feedback** → passed to the experience section-optimizer
- **Cover letter feedback** → passed to the cover-letter-writer agent
- **General/formatting feedback** → passed to all agents
- **Tone feedback** → passed to all writing agents

This ensures the user never has to repeat the same correction twice.
