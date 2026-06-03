---
name: feedback
description: >
  Save hexagonal agent app feedback proactively. MUST trigger when the user corrects architecture
  patterns, tool design, or UI component choices ("don't generate that", "always use this pattern",
  "wrong component") or confirms good output. Also trigger on explicit requests: "save this feedback",
  "show my feedback", "clear feedback", "app preferences", "hexagonal settings", "consolidate
  feedback", "bake in my preferences". Feedback loaded automatically when building hexagonal apps.
args:
  - name: action
    description: "Action to take: save, show, clear, or consolidate"
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
  python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py hexagonal-agents save-feedback
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
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py hexagonal-agents show-feedback
```

Present as a readable list grouped by category.

### Clear Feedback

Clear all feedback or feedback for a specific category:

```bash
# Clear all
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py hexagonal-agents clear-feedback

# Clear only styling feedback
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py hexagonal-agents clear-feedback styling
```

### Consolidate Feedback

Graduate stable feedback into the actual SKILL.md files, making corrections permanent. This is a
Claude-driven operation — no script needed.

**When to consolidate**: When the user says "update the plugin based on feedback", "consolidate feedback",
"bake in my preferences", or "graduate feedback into the skill".

**Process**:

1. Load all stored feedback:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py hexagonal-agents show-feedback
```

2. Read the target SKILL.md file:
   - `${CLAUDE_PLUGIN_ROOT}/skills/hexagonal-agents/SKILL.md`

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
   python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py hexagonal-agents clear-feedback <category>
   ```
   - Keep non-graduated entries untouched

6. Report what changed and what remains as runtime feedback.

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
