# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code plugin marketplace repository. It contains plugins that extend Claude Code's capabilities with specialized skills and tools. The primary plugin is `mochi-creator`, which enables creation and management of Mochi.cards flashcards through the Mochi API.

## Repository Structure

```
claude-plugins/
├── plugins/
│   └── mochi-creator/              # Mochi.cards flashcard creation plugin
│       ├── .claude-plugin/
│       │   ├── plugin.json         # Plugin metadata and configuration
│       │   └── skills/             # Symlink to skills directory
│       └── skills/
│           └── mochi-creator/
│               ├── SKILL.md        # Skill documentation and usage guide
│               ├── scripts/
│               │   └── mochi_api.py  # Python client for Mochi API
│               └── references/
│                   └── mochi_api_reference.md  # API reference docs
├── README.md                       # Marketplace installation instructions
└── CLAUDE.md                       # This file
```

## Key Architectural Concepts

### Plugin System Structure

Each plugin follows a specific directory structure:
- `.claude-plugin/plugin.json`: Contains plugin metadata (name, description, version, author, keywords)
- `skills/`: Contains one or more skills that implement the plugin's functionality
- Each skill has a `SKILL.md` file that serves as the prompt/instruction set for Claude Code

### Mochi API Client Architecture

The `mochi_api.py` script (plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py:1) is designed as both:
1. A Python module that can be imported: `from scripts.mochi_api import MochiAPI`
2. A standalone CLI tool: `python scripts/mochi_api.py list-decks`

The client uses:
- HTTP Basic Auth with the API key as username
- Request/response pattern with custom `MochiAPIError` exception
- Automatic translation between Python naming (snake_case) and Mochi API naming (kebab-case with ? suffixes for booleans)

### Authentication

All Mochi API operations require an API key stored in the `MOCHI_API_KEY` environment variable. The client will raise `MochiAPIError` if the key is not found.

## Development Commands

### Testing the Mochi API Client

```bash
# Set API key
export MOCHI_API_KEY="your_api_key_here"

# List all decks
python plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py list-decks

# Create a new deck
python plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py create-deck "Test Deck"

# List cards in a deck
python plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py list-cards <deck-id>

# Create a card
python plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py create-card <deck-id> "# Question\\n---\\nAnswer"
```

### Using the Python Module

```python
from scripts.mochi_api import MochiAPI

# Initialize (reads MOCHI_API_KEY from environment)
api = MochiAPI()

# Create a deck
deck = api.create_deck(name="Python Programming")

# Create a simple flashcard
card = api.create_card(
    content="# What is a decorator?\n---\nA function that modifies another function",
    deck_id=deck["id"],
    manual_tags=["python", "decorators"]
)

# Create template-based cards
template = api.create_template(
    name="Vocabulary",
    content="# << Word >>\n\n**Definition:** << Definition >>\n\n**Example:** << Example >>",
    fields={
        "word": {"id": "word", "name": "Word", "type": "text", "pos": "a"},
        "definition": {"id": "definition", "name": "Definition", "type": "text", "pos": "b"},
        "example": {"id": "example", "name": "Example", "type": "text", "pos": "c"}
    }
)

card = api.create_card(
    content="",
    deck_id=deck["id"],
    template_id=template["id"],
    fields={
        "word": {"id": "word", "value": "ephemeral"},
        "definition": {"id": "definition", "value": "Lasting for a very short time"},
        "example": {"id": "example", "value": "Cherry blossoms are ephemeral"}
    }
)
```

## Important Implementation Details

### Card Content Format

Cards use markdown with `---` to separate sides:
```markdown
# Question text
---
Answer text with **formatting**
```

### Field Naming Convention

The Mochi API uses Clojure-style naming:
- Kebab-case: `deck-id`, `template-id`, `parent-id`
- Boolean suffixes: `archived?`, `trashed?`, `review-reverse?`
- The Python client handles this conversion automatically

### Pagination

List operations return a `bookmark` field for pagination:
```python
result = api.list_cards(deck_id=deck_id, limit=100)
cards = result["docs"]
if result.get("bookmark"):
    next_page = api.list_cards(deck_id=deck_id, limit=100, bookmark=result["bookmark"])
```

### Soft vs Hard Delete

- Soft delete (reversible): `api.update_card(card_id, trashed=datetime.utcnow().isoformat())`
- Hard delete (permanent): `api.delete_card(card_id)`

Always prefer soft deletion for safety.

## Plugin Installation

Users install plugins from this marketplace using:

```bash
# Add the marketplace
/plugin marketplace add joshuaoliphant/claude-plugins

# Install a plugin
/plugin install mochi-creator@oliphant-plugins
```

## Error Handling

All API operations can raise `MochiAPIError`. Always wrap API calls in try-except blocks:

```python
from scripts.mochi_api import MochiAPIError

try:
    card = api.create_card(content=content, deck_id=deck_id)
except MochiAPIError as e:
    print(f"Failed to create card: {e}")
```

## Testing and Development

When developing new plugins or modifying existing ones:
1. Test the Python API client independently before integrating with Claude Code
2. Verify the skill description in `SKILL.md` accurately reflects capabilities
3. Ensure `plugin.json` metadata is complete and accurate
4. Test installation from the marketplace structure

## AI Developer Workflows (ADWs)

This project now includes ADW infrastructure for programmatic agent execution. This is the **reference implementation** used to iterate on the adw-bootstrap plugin itself.

### What ADWs Enable

- **Execute prompts programmatically**: Run Claude Code from command line scripts
- **Reusable templates**: Slash commands for common workflows (chore planning, implementation)
- **Observability**: Structured outputs in `agents/{id}/` directories for debugging
- **Iterative testing**: Dogfood the adw-bootstrap plugin by using it in its own development

### ADW Commands

Execute Claude Code prompts programmatically:

```bash
# Direct prompt execution
./adws/adw_prompt.py "analyze the plugin structure"
./adws/adw_prompt.py "review mochi_api.py" --model opus

# Run with different models
./adws/adw_prompt.py "quick check" --model haiku  # Fast & economical
./adws/adw_prompt.py "deep analysis" --model opus  # Max intelligence
./adws/adw_prompt.py "implement feature" --model sonnet  # Balanced (default)
```

### ADW Architecture

**Two-Layer Model:**
1. **Agentic Layer** (`adws/`, `.claude/`, `specs/`) - Orchestration infrastructure
2. **Application Layer** (`plugins/`) - The plugins themselves

**Core Components:**
- `adws/adw_modules/agent.py` - Subprocess execution engine
  - Invokes Claude Code CLI programmatically
  - Streams JSONL output to files
  - Automatic retry logic for transient failures
  - Smart CLI path detection (checks env, `which claude`, common locations)
- `adws/adw_prompt.py` - CLI wrapper for adhoc prompts
  - uv script with inline dependencies (PEP 723)
  - Rich console output with progress tracking
  - Multiple output formats (JSONL, JSON array, final object, summary)
- `.claude/commands/` - Slash command templates
  - `chore.md` - Create implementation plans in `specs/` directory
  - `implement.md` - Execute plans created by chore command
- `specs/` - Specification and plan documents
- `agents/` - Execution outputs and observability

**Output Structure:**
```
agents/{adw_id}/{agent_name}/
  cc_raw_output.jsonl       - Raw streaming output from Claude Code
  cc_raw_output.json         - Parsed JSON array of all messages
  cc_final_object.json       - Final result object (last message)
  custom_summary_output.json - High-level execution summary
```

### Usage Mode Configuration

**Mode A: Claude Max Subscription (Recommended for Development)**
- No configuration needed if you have Claude Max subscription
- Claude Code authenticates through your subscription
- Perfect for interactive plugin development

**Mode B: API-Based (For Automation/CI/CD)**
- Set `ANTHROPIC_API_KEY` in `.env` file
- Required for headless automation
- Use for testing workflows programmatically

```bash
# Create .env file for API mode
cp .env.sample .env
# Edit .env and add your API key
```

### Iterating on adw-bootstrap Plugin

This ADW setup serves as a **reference implementation** for testing the adw-bootstrap plugin itself:

1. **Make changes** to `plugins/adw-bootstrap/skills/adw-bootstrap/reference/` files
2. **Test changes** by tearing down and re-running setup:
   ```bash
   # Remove existing ADW infrastructure
   rm -rf adws .claude/commands/chore.md .claude/commands/implement.md specs agents .env.sample

   # Run adw-bootstrap skill again
   # (Ask Claude Code: "Set up ADWs")
   ```
3. **Validate** that generated files match expectations
4. **Iterate** on reference implementations until setup is 100% correct

### Example Workflows

**Create a plan for a plugin enhancement:**
```bash
# Generate unique ID
adw_id=$(uuidgen | cut -c1-8)

# Execute chore command (creates plan in specs/)
./adws/adw_prompt.py "/chore $adw_id 'add template support to mochi-creator'"
```

**Test adhoc prompts:**
```bash
# Quick analysis with haiku (fast)
./adws/adw_prompt.py "what skills are available in mochi-creator plugin" --model haiku

# Deep code review with opus
./adws/adw_prompt.py "review the mochi_api.py client for security issues" --model opus
```

### Observability

All executions create structured output for debugging:
- Track execution lineage with unique `adw_id`
- Inspect JSONL streams to see tool calls and responses
- Use summary JSON for high-level success/failure tracking
- Find prompts in `agents/{id}/{agent}/prompts/` directory

### Next Steps (After Minimal Phase)

The current setup is **Minimal phase**. To upgrade:

**Enhanced Phase** adds:
- SDK-based execution (`agent_sdk.py`) for better type safety
- Slash command executor (`adw_slash_command.py`)
- Compound workflows (`adw_chore_implement.py` - plan + implement in one command)
- Richer templates (feature planning, testing, TDD workflows)

**Scaled Phase** adds:
- State management across workflow phases
- Git worktree isolation
- Beads issue tracking integration (perfect for this local project)
- Multi-phase SDLC workflows
- 20+ advanced slash commands
