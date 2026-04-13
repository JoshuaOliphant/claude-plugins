---
name: feedback
description: >
  Save SDLC workflow feedback proactively. MUST trigger when the user corrects SDLC behavior ("don't
  generate tests like that", "always use this pattern", "that's not how I want specs written") or
  confirms a non-obvious approach worked ("yes exactly", "perfect"). Also trigger on explicit requests:
  "save this feedback", "show my feedback", "clear feedback", "workflow preferences", "sdlc settings",
  "consolidate feedback", "bake in my preferences". Feedback persists across sessions and is loaded
  by BDD, TDD, beads, and verification skills.
args:
  - name: action
    description: "Action to take: save, show, clear, or consolidate"
    required: false
user-invokable: true
effort: low
allowed-tools:
  - Bash
  - Read
  - Edit
---

# Autonomous SDLC Feedback Manager

Persist feedback about SDLC workflow preferences across sessions. Stored feedback is automatically
loaded by BDD, TDD, beads, and verification skills, ensuring workflow preferences carry forward.

## Actions

### Save Feedback

When the user provides feedback on SDLC workflow behavior, save it:

```bash
echo '{"category": "<category>", "feedback": "<what the user said>", "context": "<optional context>"}' | \
  python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc save-feedback
```

**Categories**: spec_writing, test_generation, tdd_workflow, bdd_workflow, verification, beads_workflow, general

**Examples**:
- "BDD specs should use business language, not technical" → `{"category": "spec_writing", "feedback": "Write BDD scenarios in business domain language — avoid implementation details like class names or API endpoints"}`
- "Don't generate integration tests unless I ask" → `{"category": "test_generation", "feedback": "Default to unit tests only — only generate integration tests when explicitly requested"}`
- "Verification should check for type errors" → `{"category": "verification", "feedback": "Always include mypy/pyright type checking in the verification stack"}`
- "Use pytest fixtures over setup methods" → `{"category": "tdd_workflow", "feedback": "Prefer pytest fixtures over setUp/tearDown class methods for test setup"}`
- "Keep beads issues concise" → `{"category": "beads_workflow", "feedback": "Beads issue descriptions should be 2-3 sentences maximum — link to specs for detail"}`
- "Red-green-refactor cycles should be smaller" → `{"category": "tdd_workflow", "feedback": "Each TDD cycle should touch at most one function — break larger changes into multiple cycles"}`

### Show Feedback

Display all stored feedback:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc show-feedback
```

Present as a readable list grouped by category.

### Clear Feedback

Clear all feedback or feedback for a specific category:

```bash
# Clear all
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc clear-feedback

# Clear only test_generation feedback
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc clear-feedback test_generation
```

### Consolidate Feedback

Graduate stable feedback into the actual SKILL.md files, making corrections permanent. This is a
Claude-driven operation — no script needed.

**When to consolidate**: When the user says "update the plugin based on feedback", "consolidate feedback",
"bake in my preferences", or "graduate feedback into the skill".

**Process**:

1. Load all stored feedback:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc show-feedback
```

2. Read the target SKILL.md files:
   - `${CLAUDE_PLUGIN_ROOT}/skills/bdd-spec/SKILL.md`
   - `${CLAUDE_PLUGIN_ROOT}/skills/bdd-generate/SKILL.md`
   - `${CLAUDE_PLUGIN_ROOT}/skills/tdd-workflow/SKILL.md`
   - `${CLAUDE_PLUGIN_ROOT}/skills/verification-stack/SKILL.md`
   - `${CLAUDE_PLUGIN_ROOT}/skills/beads-workflow/SKILL.md`

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
   python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc clear-feedback <category>
   ```
   - Keep non-graduated entries untouched

6. Report what changed and what remains as runtime feedback.

## How Feedback is Used

When autonomous-sdlc skills run, they load relevant feedback entries:

- **spec_writing** feedback → loaded by bdd-spec to guide scenario style and language
- **test_generation** feedback → loaded by bdd-generate to shape test output
- **tdd_workflow** feedback → loaded by tdd-workflow to adjust cycle size and patterns
- **bdd_workflow** feedback → loaded by bdd-spec and bdd-generate for process preferences
- **verification** feedback → loaded by verification-stack to adjust gate strictness
- **beads_workflow** feedback → loaded by beads-workflow for issue management style
- **general** feedback → applied to all SDLC skills

This ensures the user never has to repeat the same workflow preference twice.
