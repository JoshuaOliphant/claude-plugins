---
name: feedback
description: >
  Save knowledge capture/retrieval feedback proactively. MUST trigger when the user corrects capture
  behavior ("don't capture that", "wrong category", "too verbose", "not enough detail") or confirms
  a good capture ("yes, exactly like that"). Also trigger on explicit requests: "save this feedback",
  "show my feedback", "clear feedback", "knowledge preferences", "consolidate feedback", "bake in
  my preferences". Feedback loaded by compound-capture and compound-retrieve across sessions.
args:
  - name: action
    description: "Action to take: save, show, clear, or consolidate"
    required: false
user-invokable: true
---

# Compound Knowledge Feedback Manager

Persist feedback about knowledge capture and retrieval across sessions. Stored feedback is automatically
loaded when compound-capture or compound-retrieve runs, ensuring corrections are never repeated.

## Actions

### Save Feedback

When the user provides feedback on capture or retrieval behavior, save it:

```bash
echo '{"category": "<category>", "feedback": "<what the user said>", "context": "<optional context>"}' | \
  python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py compound-knowledge save-feedback
```

**Categories**: capture_format, categorization, triviality_threshold, cross_references, retrieval_depth, principle_style, general

**Examples**:
- "Don't capture trivial one-line fixes" → `{"category": "triviality_threshold", "feedback": "Raise the bar — only capture solutions that required multiple investigation steps"}`
- "Always include code examples" → `{"category": "capture_format", "feedback": "Include inline code examples in the solution body, not just descriptions"}`
- "Stop putting patterns in debugging/" → `{"category": "categorization", "feedback": "Design patterns belong in patterns/, even if discovered during debugging"}`
- "Show more results when searching" → `{"category": "retrieval_depth", "feedback": "Return top 5-7 results instead of top 3 when searching solutions"}`
- "Principles should be shorter" → `{"category": "principle_style", "feedback": "Keep principle statements to one sentence maximum"}`

### Show Feedback

Display all stored feedback:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py compound-knowledge show-feedback
```

Present as a readable list grouped by category.

### Clear Feedback

Clear all feedback or feedback for a specific category:

```bash
# Clear all
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py compound-knowledge clear-feedback

# Clear only categorization feedback
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py compound-knowledge clear-feedback categorization
```

### Consolidate Feedback

Graduate stable feedback into the actual SKILL.md files, making corrections permanent. This is a
Claude-driven operation — no script needed.

**When to consolidate**: When the user says "update the plugin based on feedback", "consolidate feedback",
"bake in my preferences", or "graduate feedback into the skill".

**Process**:

1. Load all stored feedback:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py compound-knowledge show-feedback
```

2. Read the target SKILL.md files that the feedback applies to:
   - `${CLAUDE_PLUGIN_ROOT}/skills/compound-capture/SKILL.md`
   - `${CLAUDE_PLUGIN_ROOT}/skills/compound-retrieve/SKILL.md`

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
   python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py compound-knowledge clear-feedback <category>
   ```
   - Keep non-graduated entries untouched

6. Report what changed and what remains as runtime feedback.

## How Feedback is Used

When compound-capture runs, it loads all feedback entries and applies them:

- **capture_format** feedback → adjusts the structure and detail level of solution files
- **categorization** feedback → guides which directory a solution is filed into
- **triviality_threshold** feedback → calibrates what gets captured vs skipped
- **cross_references** feedback → adjusts how aggressively related solutions are linked
- **principle_style** feedback → shapes how engineering principles are worded
- **general** feedback → applied to all capture and retrieval operations

When compound-retrieve runs, it loads retrieval-related feedback:

- **retrieval_depth** feedback → adjusts how many results are surfaced
- **general** feedback → applied to result formatting and presentation

This ensures the user never has to repeat the same correction twice.
