---
name: feedback
description: >
  Save agent-skills workflow feedback proactively. MUST trigger when the user corrects how a
  visual plan/recap, recap status block, orchestration, autonomy, docs-first, or review skill
  behaves ("recaps are too long", "always web-search the docs first", "don't stop to ask",
  "plans should lead with the wireframe") or confirms good output. Also trigger on explicit
  requests: "save this feedback", "show my feedback", "clear feedback", "agent-skills
  preferences", "consolidate feedback", "bake in my preferences". Feedback loaded automatically
  when running these skills.
args:
  - name: action
    description: "Action to take: save, show, clear, or consolidate"
    required: false
user-invokable: true
---

# Agent-Skills Feedback Manager

Persist feedback about how the agent-skills workflow skills should behave across sessions.
Stored feedback is loaded when those skills run, so the user never has to repeat a preference.

## Actions

### Save Feedback

When the user corrects or confirms how an agent-skill behaves, save it:

```bash
echo '{"category": "<category>", "feedback": "<what the user said>", "context": "<optional context>"}' | \
  python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py agent-skills save-feedback
```

**Categories**: plan_style, recap_style, status_format, orchestration, autonomy, docs_discipline, review, usage_limits, general

**Examples**:
- "Recaps are too long, keep them lean" → `{"category": "recap_style", "feedback": "Keep visual-recap output lean — prefer the headline wireframe + key-change diffs over exhaustive prose"}`
- "Always lead plans with the wireframe" → `{"category": "plan_style", "feedback": "For UI plans, lead with the top canvas wireframe before document-body sections"}`
- "Don't stop to ask, use best judgment" → `{"category": "autonomy", "feedback": "Default to plow-ahead: convert routine ambiguity into stated assumptions, stop only for true blockers"}`
- "Web-search the official docs before guessing" → `{"category": "docs_discipline", "feedback": "Always read-the-damn-docs: web-search current official docs before implementing against any third-party API"}`
- "Use red/green/yellow at the end of every response" → `{"category": "status_format", "feedback": "End substantive responses with a quick-recap red/yellow/green status block"}`
- "Delegate heavy reading to cheap subagents" → `{"category": "orchestration", "feedback": "Reserve the expensive model for judgment; delegate research/coding/testing to cheaper subagents"}`

### Show Feedback

Display all stored feedback:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py agent-skills show-feedback
```

Present as a readable list grouped by category.

### Clear Feedback

Clear all feedback or feedback for a specific category:

```bash
# Clear all
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py agent-skills clear-feedback

# Clear only recap_style feedback
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py agent-skills clear-feedback recap_style
```

### Consolidate Feedback

Graduate stable feedback into the actual SKILL.md files, making corrections permanent. This is a
Claude-driven operation — no script needed.

**When to consolidate**: When the user says "update the skills based on feedback", "consolidate
feedback", "bake in my preferences", or "graduate feedback into the skill".

**Process**:

1. Load all stored feedback:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py agent-skills show-feedback
```

2. Read the target SKILL.md for the skill the feedback is about, under
   `${CLAUDE_PLUGIN_ROOT}/skills/<skill-name>/SKILL.md` (e.g. `skills/visual-recap/SKILL.md`
   for recap_style, `skills/plow-ahead/SKILL.md` for autonomy).

3. For each feedback entry, decide:
   - **Consolidate**: Universal preferences, repeated corrections, rules that always apply.
   - **Keep as runtime feedback**: Situational or context-dependent preferences.

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
   - Edit the target SKILL.md files using the Edit tool.
   - Clear only the graduated feedback entries:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py agent-skills clear-feedback <category>
   ```
   - Keep non-graduated entries untouched.

6. Report what changed and what remains as runtime feedback.

## How Feedback is Used

When an agent-skill runs, load stored feedback and apply the matching category:

- **plan_style** → shapes visual-plan surface choice, layout, and what leads the document.
- **recap_style** → calibrates visual-recap length, wireframe choices, and diff selection.
- **status_format** → adjusts the quick-recap status-block convention.
- **orchestration** → tunes efficient-fable / efficient-frontier delegation strategy.
- **autonomy** → adjusts plow-ahead's stop-vs-assume threshold.
- **docs_discipline** → reinforces read-the-damn-docs triggers.
- **review** → shapes agent-watchdog / plan-arbiter scope and verdict style.
- **usage_limits** → calibrates stay-within-limits pause/resume behavior.
- **general** → applied across all agent-skills.

This ensures the user never has to repeat the same workflow preference twice.
