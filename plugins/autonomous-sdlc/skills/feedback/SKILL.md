---
name: feedback
description: >
  Save, view, or manage feedback about SDLC workflow preferences. Feedback persists across sessions
  and is automatically loaded by BDD, TDD, beads, and verification skills. Use when the user wants
  to adjust spec writing style, test generation patterns, workflow behavior, or verification strictness.
  Trigger phrases include "remember this for next time", "save this feedback", "don't generate tests
  like that", "always use this pattern", "show my feedback", "clear feedback", "workflow preferences",
  and "sdlc settings".
args:
  - name: action
    description: "Action to take: save, show, or clear"
    required: false
user-invokable: true
---

# Autonomous SDLC Feedback Manager

Persist feedback about SDLC workflow preferences across sessions. Stored feedback is automatically
loaded by BDD, TDD, beads, and verification skills, ensuring workflow preferences carry forward.

## Actions

### Save Feedback

When the user provides feedback on SDLC workflow behavior, save it:

```bash
echo '{"category": "<category>", "feedback": "<what the user said>", "context": "<optional context>"}' | \
  python ${PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc save-feedback
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
python ${PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc show-feedback
```

Present as a readable list grouped by category.

### Clear Feedback

Clear all feedback or feedback for a specific category:

```bash
# Clear all
python ${PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc clear-feedback

# Clear only test_generation feedback
python ${PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc clear-feedback test_generation
```

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
