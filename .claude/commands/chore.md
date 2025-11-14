# Chore Planning

Create a plan to complete the chore using the specified markdown `Plan Format`. Research the codebase and create a thorough plan.

## Variables
adw_id: $1
prompt: $2

## Instructions

- If the adw_id or prompt is not provided, stop and ask the user to provide them.
- Create a plan to complete the chore described in the `prompt`
- The plan should be simple, thorough, and precise
- Create the plan in the `specs/` directory with filename: `chore-{adw_id}-{descriptive-name}.md`
  - Replace `{descriptive-name}` with a short, descriptive name based on the chore (e.g., "update-readme", "add-logging", "refactor-agent")
- Research the codebase starting with `README.md` and `CLAUDE.md`
- Replace every <placeholder> in the `Plan Format` with the requested value

## Codebase Structure

This is a Claude Code plugin marketplace repository:
- `README.md` - Marketplace overview and plugin installation instructions
- `CLAUDE.md` - Development guidance and architectural documentation
- `plugins/` - Claude Code plugins (mochi-creator, adw-bootstrap)
  - Each plugin has `.claude-plugin/plugin.json` for metadata
  - Each plugin has `skills/` directory containing SKILL.md files
- `adws/` - AI Developer Workflow scripts for programmatic agent execution
- `.claude/commands/` - Claude Code slash command templates
- `specs/` - Specification and plan documents

## Plan Format

```md
# Chore: <chore name>

## Metadata
adw_id: `{adw_id}`
prompt: `{prompt}`

## Chore Description
<describe the chore in detail based on the prompt>

## Relevant Files
Use these files to complete the chore:

<list files relevant to the chore with bullet points explaining why. Include new files to be created under an h3 'New Files' section if needed>

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

<list step by step tasks as h3 headers with bullet points. Start with foundational changes then move to specific changes. Last step should validate the work>

### 1. <First Task Name>
- <specific action>
- <specific action>

### 2. <Second Task Name>
- <specific action>
- <specific action>

## Validation Commands
Execute these commands to validate the chore is complete:

<list specific commands to validate the work. Be precise about what to run>
- Example: `uv run python scripts/mochi_api.py list-decks` - Test Mochi API connectivity
- Example: `uv run ruff check .` - Ensure code quality

## Notes
<optional additional context or considerations>
```

## Chore
Use the chore description from the `prompt` variable.

## Report

Return the path to the plan file created.
