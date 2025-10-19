---
name: mochi-creator
description: This skill should be used when working with Mochi.cards flashcard system. Use this skill to create flashcards, manage decks (collections), and create templates for structured cards. Trigger when user requests to create Mochi cards, add to Mochi decks, organize flashcards, or work with spaced repetition study materials.
---

# Mochi Creator

## Overview

This skill enables creation and management of flashcards, decks, and templates in Mochi.cards, a spaced repetition learning system. Use this skill to transform content into study materials, organize learning resources into deck hierarchies, and create reusable card templates.

## Quick Start

### Setup

Before using this skill, set the Mochi API key as an environment variable:

```bash
export MOCHI_API_KEY="your_api_key_here"
```

To obtain an API key:
1. Open the Mochi.cards application
2. Navigate to Account Settings
3. Locate the API Keys section
4. Generate a new API key

### Using the Python Script

The `scripts/mochi_api.py` script provides a complete Python interface to the Mochi API. Import and use it in Python code:

```python
from scripts.mochi_api import MochiAPI

# Initialize the client (reads MOCHI_API_KEY from environment)
api = MochiAPI()

# Create a deck
deck = api.create_deck(name="Python Programming")

# Create a card in that deck
card = api.create_card(
    content="# What is a list comprehension?\n---\nA concise way to create lists in Python",
    deck_id=deck["id"],
    manual_tags=["python", "syntax"]
)
```

Or execute it directly from command line for testing:

```bash
python scripts/mochi_api.py list-decks
python scripts/mochi_api.py create-deck "My Study Deck"
python scripts/mochi_api.py list-cards <deck-id>
```

## Core Tasks

### Creating Simple Flashcards

For basic question-and-answer flashcards, create cards with markdown content using `---` to separate card sides.

**Example user requests:**
- "Create a Mochi card about Python decorators"
- "Add a flashcard to my Python deck explaining lambda functions"
- "Make flashcards from these notes"

**Implementation approach:**

1. List existing decks to get deck IDs or create a new deck if needed:
```python
decks = api.list_decks()
# Or create new deck
deck = api.create_deck(name="Python Programming")
deck_id = deck["id"]
```

2. Format content with markdown and side separators:
```python
content = """# What are Python decorators?
---
Functions that modify the behavior of other functions or methods.
They use the @decorator syntax above function definitions.

Example:
@staticmethod
def my_function():
    pass
"""
```

3. Create the card with optional tags:
```python
card = api.create_card(
    content=content,
    deck_id=deck_id,
    manual_tags=["python", "functions", "decorators"]
)
```

**Multi-card creation from text:**

When creating multiple cards from a document or conversation:
1. Parse or chunk the content into logical learning units
2. Format each as question/answer or concept/explanation
3. Create cards in a loop, handling each API response
4. Report success/failure for each card created

### Creating Template-Based Cards

For structured, repeatable card formats (vocabulary, definitions, examples), use templates with fields.

**Example user requests:**
- "Create vocabulary flashcards with word, definition, and example"
- "Make a template for programming concepts with name, description, and code example"
- "Use the Basic Flashcard template to create cards"

**Implementation approach:**

1. Create or retrieve a template:
```python
# Create a new template
template = api.create_template(
    name="Vocabulary Card",
    content="# << Word >>\n\n**Definition:** << Definition >>\n\n**Example:** << Example >>",
    fields={
        "word": {
            "id": "word",
            "name": "Word",
            "type": "text",
            "pos": "a"
        },
        "definition": {
            "id": "definition",
            "name": "Definition",
            "type": "text",
            "pos": "b",
            "options": {"multi-line?": True}
        },
        "example": {
            "id": "example",
            "name": "Example",
            "type": "text",
            "pos": "c",
            "options": {"multi-line?": True}
        }
    }
)
```

2. Create cards using the template:
```python
card = api.create_card(
    content="",  # Content can be empty when using fields
    deck_id=deck_id,
    template_id=template["id"],
    fields={
        "word": {
            "id": "word",
            "value": "ephemeral"
        },
        "definition": {
            "id": "definition",
            "value": "Lasting for a very short time; temporary"
        },
        "example": {
            "id": "example",
            "value": "The beauty of cherry blossoms is ephemeral, lasting only a few weeks."
        }
    }
)
```

**Reusing existing templates:**

1. List available templates:
```python
templates = api.list_templates()
for template in templates["docs"]:
    print(f"{template['name']}: {template['id']}")
```

2. Retrieve template details to see field structure:
```python
template = api.get_template(template_id)
field_ids = list(template["fields"].keys())
```

3. Create cards matching the template's field structure

### Managing Decks

Organize cards into hierarchical deck structures for better content organization.

**Example user requests:**
- "Create a deck for studying Spanish"
- "Organize these cards into a Python → Data Structures subdeck"
- "List my existing Mochi decks"

**Implementation approach:**

**Creating decks:**
```python
# Top-level deck
deck = api.create_deck(
    name="Programming",
    sort=1
)

# Nested subdeck
subdeck = api.create_deck(
    name="Python",
    parent_id=deck["id"],
    sort=1
)
```

**Listing decks:**
```python
result = api.list_decks()
for deck in result["docs"]:
    parent = f" (under {deck.get('parent-id', 'root')})" if deck.get("parent-id") else ""
    print(f"{deck['name']}: {deck['id']}{parent}")

# Handle pagination if needed
if result.get("bookmark"):
    next_page = api.list_decks(bookmark=result["bookmark"])
```

**Updating deck properties:**
```python
# Archive a deck
api.update_deck(deck_id, archived=True)

# Change deck display settings
api.update_deck(
    deck_id,
    cards_view="grid",
    sort_by="updated-at",
    show_sides=True
)

# Reorganize deck hierarchy
api.update_deck(deck_id, parent_id=new_parent_id)
```

**Deck organization strategies:**
- Use hierarchical structures: Subject → Topic → Subtopic
- Set `sort` field numerically to control deck ordering
- Archive completed decks instead of deleting them
- Use `archived?` to hide decks from active review

### Batch Operations

Create multiple cards efficiently from source materials like notes, documents, or conversations.

**Example user requests:**
- "Turn this conversation into Mochi flashcards"
- "Create cards from these 20 definitions"
- "Import my study notes into Mochi"

**Implementation approach:**

1. Parse source content into individual card items
2. Identify or create target deck
3. Determine if template-based or simple cards are appropriate
4. Create cards in sequence with error handling:

```python
def create_cards_from_list(items, deck_id, template_id=None):
    """Create multiple cards with error handling."""
    results = {"success": [], "failed": []}

    for item in items:
        try:
            if template_id:
                card = api.create_card(
                    content="",
                    deck_id=deck_id,
                    template_id=template_id,
                    fields=item["fields"]
                )
            else:
                card = api.create_card(
                    content=item["content"],
                    deck_id=deck_id,
                    manual_tags=item.get("tags", [])
                )
            results["success"].append(card["id"])
        except Exception as e:
            results["failed"].append({"item": item, "error": str(e)})

    return results
```

5. Report results to user with success count and any errors

**Content extraction strategies:**
- Split text by headers or numbered lists for question/answer pairs
- Extract key terms and definitions from formatted documents
- Parse conversation history for teaching moments or explanations
- Identify code examples and create cards with syntax and explanation

### Interactive Card Creation

Guide users through card creation with clarifying questions when details are ambiguous.

**Example user requests:**
- "Help me create some flashcards"
- "I want to study biology with Mochi"

**Implementation approach:**

1. Determine what information is needed:
   - Which deck to add to (list existing or create new)
   - Card format (simple or template-based)
   - Content source (manual input, existing notes, conversation)
   - Tags and organization preferences

2. Ask targeted questions to gather requirements:
   - "Which deck should these cards go in? [list existing decks]"
   - "Would you like simple Q&A cards or structured cards with a template?"
   - "What content should I turn into cards?"

3. Create cards based on gathered information

4. Offer to continue or adjust:
   - "I've created 5 cards in your Biology deck. Would you like to add more?"
   - "Should I use a different template format?"

## Advanced Features

### Card Positioning

Control card order within decks using the `pos` field with lexicographic sorting:

```python
# Cards sort lexicographically by pos field
card1 = api.create_card(content="First card", deck_id=deck_id, pos="a")
card2 = api.create_card(content="Third card", deck_id=deck_id, pos="c")

# Insert between existing cards
card_between = api.create_card(content="Second card", deck_id=deck_id, pos="b")
```

### Tagging Strategies

Tags can be added inline in content or via `manual_tags`:

```python
# Inline tags in content
content = "# What is Python?\n---\nA programming language #python #programming"

# Manual tags (preferred for programmatic creation)
card = api.create_card(
    content="# What is Python?\n---\nA programming language",
    deck_id=deck_id,
    manual_tags=["python", "programming", "basics"]
)
```

Use manual tags when:
- Creating cards programmatically
- Tags don't fit naturally in content
- Maintaining clean card appearance
- Need to update tags separately from content

### Soft Delete vs Hard Delete

Prefer soft deletion for safety:

```python
# Soft delete (reversible)
from datetime import datetime
api.update_card(card_id, trashed=datetime.utcnow().isoformat())

# Undelete
api.update_card(card_id, trashed=None)

# Hard delete (permanent)
api.delete_card(card_id)  # Cannot be undone
```

### Pagination Handling

Handle pagination for large collections:

```python
def get_all_cards(deck_id):
    """Retrieve all cards from a deck, handling pagination."""
    all_cards = []
    bookmark = None

    while True:
        result = api.list_cards(deck_id=deck_id, limit=100, bookmark=bookmark)
        all_cards.extend(result["docs"])

        bookmark = result.get("bookmark")
        if not bookmark or not result["docs"]:
            break

    return all_cards
```

## Common Patterns

### Pattern: Topic Extraction

Extract topics from a document and create organized flashcards:

1. Identify main topics/sections
2. Create a deck for the subject
3. Create subdeck for each major topic
4. Generate cards from content within each topic
5. Tag cards with relevant concepts

### Pattern: Vocabulary Lists

Transform vocabulary lists into flashcards:

1. Create or reuse vocabulary template
2. Parse vocabulary source (spreadsheet, document, etc.)
3. Create cards using template fields
4. Group into appropriate decks by category/difficulty
5. Tag with language and proficiency level

### Pattern: Conversation Capture

Turn teaching moments from conversations into cards:

1. Review conversation history for explanations
2. Identify distinct concepts explained
3. Format as question/answer pairs
4. Create cards in relevant topic deck
5. Tag with context from conversation

## Error Handling

Handle API errors gracefully:

```python
from scripts.mochi_api import MochiAPIError

try:
    card = api.create_card(content=content, deck_id=deck_id)
except MochiAPIError as e:
    # Report specific error to user
    print(f"Failed to create card: {e}")
    # Possibly retry or ask for corrected input
```

Common errors:
- Missing required fields (content, deck-id)
- Invalid deck or template IDs
- Validation failures on field values
- Network connectivity issues

## Resources

### scripts/mochi_api.py

Complete Python client for the Mochi API. Provides classes and functions for:
- `MochiAPI`: Main client class with methods for all operations
- `create_card()`, `update_card()`, `delete_card()`: Card operations
- `create_deck()`, `update_deck()`, `delete_deck()`: Deck operations
- `create_template()`, `get_template()`, `list_templates()`: Template operations
- `list_cards()`, `list_decks()`: Listing with pagination support

Execute directly for command-line testing or import as a module for programmatic use.

### references/mochi_api_reference.md

Detailed API reference documentation including:
- Complete field type reference for templates
- Deck sort and view options
- Card content markdown syntax
- Positioning and tagging strategies
- Pagination details
- Error handling patterns
- Best practices for API usage

Consult this reference when:
- Creating complex templates with specialized field types
- Implementing advanced sorting or display options
- Handling edge cases or errors
- Optimizing API usage patterns
