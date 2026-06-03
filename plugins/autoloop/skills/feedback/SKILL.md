---
name: feedback
description: >
  Save autoloop experiment feedback proactively. MUST trigger when the user corrects loop design
  ("don't use that metric", "always include this gate", "wrong quality gate") or confirms good
  output. Also trigger on explicit requests: "save this feedback", "show my feedback", "clear
  feedback", "loop preferences", "autoloop settings", "consolidate feedback", "bake in my
  preferences". Feedback loaded automatically when designing new experiment loops.
args:
  - name: action
    description: "Action to take: save, show, clear, or consolidate"
    required: false
user-invokable: true
---

# Autoloop Feedback Manager

Persist feedback about experiment loop design across sessions. Stored feedback is automatically
loaded when autoloop designs new loops, ensuring design preferences carry forward.

## Actions

### Save Feedback

When the user provides feedback on loop design or execution, save it:

```bash
echo '{"category": "<category>", "feedback": "<what the user said>", "context": "<optional context>"}' | \
  python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autoloop save-feedback
```

**Categories**: loop_design, metrics, quality_gates, runner_script, time_budget, change_strategy, general

**Examples**:
- "Always include type checking as a gate" → `{"category": "quality_gates", "feedback": "Include mypy type checking as a quality gate in all Python autoloops"}`
- "Don't use coverage as a primary metric" → `{"category": "metrics", "feedback": "Avoid test coverage as primary metric — it leads to low-value tests. Use as secondary only"}`
- "Keep time budgets under 2 minutes" → `{"category": "time_budget", "feedback": "Prefer experiments that complete in under 2 minutes for faster iteration"}`
- "The runner script should always log to stderr" → `{"category": "runner_script", "feedback": "Runner scripts should redirect verbose output to stderr, keep stdout for METRIC lines only"}`
- "Be more conservative with changes" → `{"category": "change_strategy", "feedback": "Prefer small, focused changes per iteration over ambitious rewrites"}`

### Show Feedback

Display all stored feedback:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autoloop show-feedback
```

Present as a readable list grouped by category.

### Clear Feedback

Clear all feedback or feedback for a specific category:

```bash
# Clear all
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autoloop clear-feedback

# Clear only metrics feedback
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autoloop clear-feedback metrics
```

### Consolidate Feedback

Graduate stable feedback into the actual SKILL.md files, making corrections permanent. This is a
Claude-driven operation — no script needed.

**When to consolidate**: When the user says "update the plugin based on feedback", "consolidate feedback",
"bake in my preferences", or "graduate feedback into the skill".

**Process**:

1. Load all stored feedback:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autoloop show-feedback
```

2. Read the target SKILL.md file:
   - `${CLAUDE_PLUGIN_ROOT}/skills/autoloop/SKILL.md`

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
   python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autoloop clear-feedback <category>
   ```
   - Keep non-graduated entries untouched

6. Report what changed and what remains as runtime feedback.

## How Feedback is Used

When autoloop designs a new experiment loop, it loads all feedback entries and applies them:

- **loop_design** feedback → adjusts overall loop structure and iteration strategy
- **metrics** feedback → guides metric selection and direction (minimize/maximize)
- **quality_gates** feedback → ensures preferred gates are included or excluded
- **runner_script** feedback → adjusts runner script generation (logging, output format)
- **time_budget** feedback → calibrates experiment duration and timeout settings
- **change_strategy** feedback → shapes the allowed change types in program.md
- **general** feedback → applied to all aspects of loop design

This ensures the user never has to repeat the same design preference twice.
