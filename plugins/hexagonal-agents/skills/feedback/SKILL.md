---
name: feedback
description: >
  Save, view, or manage feedback about hexagonal agent application preferences. Feedback persists
  across sessions and is automatically loaded when building new hexagonal agent apps. Use when the
  user wants to adjust architecture patterns, tool design, UI components, or skill file conventions.
  Trigger phrases include "remember this for next time", "save this feedback", "always use this pattern",
  "don't generate that", "show my feedback", "clear feedback", "app preferences", and "hexagonal settings".
args:
  - name: action
    description: "Action to take: save, show, or clear"
    required: false
user-invokable: true
---

# Hexagonal Agents Feedback Manager

Persist feedback about hexagonal agent app design across sessions. Stored feedback is automatically
loaded when scaffolding new apps, ensuring architecture and UI preferences carry forward.

## Actions

### Save Feedback

When the user provides feedback on generated apps, save it:

```bash
echo '{"category": "<category>", "feedback": "<what the user said>", "context": "<optional context>"}' | \
  python ${PLUGIN_ROOT}/scripts/feedback_manager.py hexagonal-agents save-feedback
```

**Categories**: architecture, tools, skill_file, ui_components, styling, agent_behavior, general

**Examples**:
- "Always use async tool handlers" → `{"category": "tools", "feedback": "All MCP tool handlers must be async, even for simple operations"}`
- "The skill file needs more HTML examples" → `{"category": "skill_file", "feedback": "Include at least 3 full HTML examples per component type in the skill file"}`
- "Use dark mode by default" → `{"category": "styling", "feedback": "Default Tailwind theme should use dark mode color palette"}`
- "Agent keeps outputting markdown instead of HTML" → `{"category": "agent_behavior", "feedback": "Add stronger HTML-only instructions — repeat 'output raw HTML only' at least 3 times in skill file"}`
- "Separate tools into domain modules" → `{"category": "architecture", "feedback": "Split tools.py into domain-specific modules (e.g., user_tools.py, item_tools.py) for apps with >5 tools"}`

### Show Feedback

Display all stored feedback:

```bash
python ${PLUGIN_ROOT}/scripts/feedback_manager.py hexagonal-agents show-feedback
```

Present as a readable list grouped by category.

### Clear Feedback

Clear all feedback or feedback for a specific category:

```bash
# Clear all
python ${PLUGIN_ROOT}/scripts/feedback_manager.py hexagonal-agents clear-feedback

# Clear only styling feedback
python ${PLUGIN_ROOT}/scripts/feedback_manager.py hexagonal-agents clear-feedback styling
```

## How Feedback is Used

When hexagonal-agents scaffolds a new app, it loads all feedback entries and applies them:

- **architecture** feedback → adjusts project structure and module organization
- **tools** feedback → guides MCP tool design patterns and conventions
- **skill_file** feedback → shapes the agent's UI skill file content and examples
- **ui_components** feedback → adjusts which components are included and how they're structured
- **styling** feedback → calibrates Tailwind theme and design system defaults
- **agent_behavior** feedback → strengthens or adjusts agent instructions
- **general** feedback → applied to all aspects of app generation

This ensures the user never has to repeat the same design preference twice.
