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
