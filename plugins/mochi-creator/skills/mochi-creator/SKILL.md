---
name: mochi-creator
description: >
  Create evidence-based spaced repetition flashcards using cognitive science principles from Andy
  Matuschak's research. Use when the user wants to create Mochi cards, flashcards, study materials,
  or mentions learning, memorization, spaced repetition, SRS, Anki-style cards, or knowledge
  retention. Trigger phrases include "make flashcards", "create Mochi cards", "I need to memorize
  this", "help me study", "turn this into flashcards", "create study materials", "I want to remember
  this", and "make SRS cards". Applies the 5 properties of effective prompts (focused, precise,
  consistent, tractable, effortful) to ensure cards actually work for long-term retention.
---

# Mochi Creator

## Goal

Transform content into evidence-based Mochi.cards flashcards that produce lasting retention. Every card created must satisfy the 5 properties of effective prompts: focused, precise, consistent, tractable, and effortful.

**Core Philosophy**: Writing prompts for spaced repetition is task design. You're creating recurring retrieval tasks for your future self. Bad prompts waste time and fail to build lasting memory. Great prompts compound learning over years.

## Dependencies

### Tools

- **`scripts/mochi_api.py`** — Python client for the Mochi API. Both importable (`from scripts.mochi_api import MochiAPI`) and CLI-executable (`python scripts/mochi_api.py list-decks`). Handles auth, field naming conventions (snake_case → kebab-case), and pagination.

### Connectors

- **Mochi API** — Requires `MOCHI_API_KEY` environment variable (obtain from Mochi.cards → Account Settings → API Keys). Uses HTTP Basic Auth.

### Setup

```bash
export MOCHI_API_KEY="your_api_key_here"
```

## Context

### The Five Properties of Effective Prompts

Every prompt must satisfy all five (from Andy Matuschak's research):

1. **Focused** — One detail at a time. Write 3-5 cards instead of 1 comprehensive card.
2. **Precise** — Specific questions demand specific answers. Avoid "interesting", "important", "tell me about".
3. **Consistent** — Should produce the same answer each time. Avoid "give an example of X".
4. **Tractable** — ~90% success rate. Break down if struggling, add cues. Remove scaffolding if too easy.
5. **Effortful** — Must require actual memory retrieval, not trivial inference or pattern matching.

### Quality Validation Checklist

Before creating each card, verify:

- [ ] **Focused**: Tests exactly one detail?
- [ ] **Precise**: Question is specific, answer is unambiguous?
- [ ] **Consistent**: Will produce the same answer each time?
- [ ] **Tractable**: Learner can answer correctly ~90% of the time?
- [ ] **Effortful**: Requires actual memory retrieval?
- [ ] **Emotional**: Learner genuinely cares about remembering this?

If any checkbox fails, revise before creating the card.

### Anti-Patterns

Reject these on sight:

| Anti-Pattern | Example | Fix |
|---|---|---|
| Binary (yes/no) | "Is encapsulation important?" | "What benefit does encapsulation provide?" |
| Pattern-matching | Long verbose question → obvious answer | Keep question short and direct |
| Unfocused | "Features, benefits, and drawbacks of X?" | Separate card per detail |
| Vague | "Tell me about async/await" | "What problem does async/await solve?" |
| Trivial | "What does URL stand for?" | "Why do URLs encode spaces as %20?" |

### Deep Reference

For full cognitive science background, knowledge-type strategies (factual, conceptual, procedural, salience), the five conceptual lenses, and research citations, consult:

→ **`references/prompt_design_principles.md`**

## Process

### Step 0: Load Stored Feedback

Load any stored feedback preferences before starting:

```bash
python ${PLUGIN_ROOT}/scripts/feedback_manager.py mochi-creator show-feedback
```

If feedback entries exist, apply them throughout card creation:
- **card_quality** → adjust the bar for what cards get created
- **difficulty** → calibrate tractability — how challenging cards should be
- **formatting** → shape card format (Q&A vs cloze, markdown style)
- **deck_organization** → guide deck/subdeck structure and tagging
- **topics** → inform current study focus and priority areas
- **batch_size** → limit how many cards are created per session
- **general** → apply to all aspects of card creation

### Step 1: Establish Context

Determine the scope and emotional connection before drafting any cards.

**Ask the user:**
- What content to transform into cards (notes, conversation, topic)
- Which deck to target (list existing with `api.list_decks()` or create new)
- What type of knowledge: factual, conceptual, procedural, or salience
- "Do you actually care about remembering this in six months? Why?"

If the user seems unmotivated or creating cards "because they should," push back gently. Emotional connection is primary — boredom leads to abandonment of the entire system.

**Identify card format:**
- **Simple cards** — markdown with `---` separator between sides
- **Template-based cards** — structured fields for repeatable formats (vocabulary, definitions)

```python
from scripts.mochi_api import MochiAPI, MochiAPIError

api = MochiAPI()

# List existing decks
decks = api.list_decks()

# Or create a new deck
deck = api.create_deck(name="Python Programming")
deck_id = deck["id"]
```

### Step 2: Draft Cards Using Prompt Design Principles

Apply knowledge-type appropriate strategies. Always follow the "More Than You Think" rule: write 3-5 focused prompts instead of 1 comprehensive prompt.

**For factual knowledge** — Break into atomic units:
```python
# Instead of one card listing all ingredients, create focused cards:
facts = [
    ("What is the primary dry ingredient in chocolate chip cookies?", "Flour"),
    ("What fat is used in chocolate chip cookies?", "Butter"),
    ("What two sweeteners are used?", "White sugar and brown sugar"),
]
```

**For conceptual knowledge** — Use multiple lenses (attributes, similarities, parts, causes, significance):
```python
# Approach a concept from 5 angles for robust understanding
cards = [
    ("What is the core attribute of dependency injection?",
     "Dependencies are provided from outside rather than created internally"),
    ("How does dependency injection differ from service locator?",
     "DI pushes dependencies in, service locator pulls them out"),
    ("What problem does dependency injection solve?",
     "Makes code testable by allowing mock dependencies to be injected"),
]
```

**For procedural knowledge** — Focus on transitions, rationale, and timing (not rote steps):
```python
# Focus on WHY and WHEN, not step numbers
cards = [
    ("Why do you autolyse before adding salt?",
     "Salt inhibits gluten development; autolyse allows gluten to form first"),
    ("What indicates sourdough is ready for shaping?",
     "50-100% volume increase, jiggly texture, small bubbles on surface"),
]
```

**For salience prompts** — Context-based application for behavioral change:
```python
# Answers may vary — experimental, less well-researched
cards = [
    ("What's one situation this week where you could apply first principles thinking?",
     "(Give an answer specific to your current work context)"),
]
```

For detailed cognitive science strategies per knowledge type, consult:

→ **`references/prompt_design_principles.md`**

For ready-to-use Python helper functions per knowledge type (`create_concept_cards_five_lenses()`, `create_procedure_cards()`, etc.), consult:

→ **`references/knowledge_type_templates.md`**

### Human Checkpoint: Review Drafted Cards

**Present all drafted cards to the user before creating them.** For each card, show:

- The question and answer
- Which quality property it primarily exercises
- Any flags (e.g., "this might be unfocused — should we split?")

Flag quality issues proactively:
- "I notice this prompt asks about features AND drawbacks. Let me split it."
- "This question is binary (yes/no). Let me rephrase as open-ended."
- "This might be too trivial. Let me make it more effortful."

**Wait for user approval before proceeding to Step 3.**

### Step 3: Create Cards via Mochi API

Create approved cards with error handling. Use tags for organization.

**Simple cards:**
```python
card = api.create_card(
    content="# What problem does dependency injection solve?\n---\nMakes code testable by allowing mock dependencies to be injected",
    deck_id=deck_id,
    manual_tags=["design-patterns", "dependency-injection"]
)
```

**Template-based cards:**
```python
# Create or retrieve a template
template = api.create_template(
    name="Vocabulary Card",
    content="# << Word >>\n\n**Definition:** << Definition >>\n\n**Example:** << Example >>",
    fields={
        "word": {"id": "word", "name": "Word", "type": "text", "pos": "a"},
        "definition": {"id": "definition", "name": "Definition", "type": "text", "pos": "b",
                       "options": {"multi-line?": True}},
        "example": {"id": "example", "name": "Example", "type": "text", "pos": "c",
                    "options": {"multi-line?": True}}
    }
)

# Create cards using the template
card = api.create_card(
    content="",
    deck_id=deck_id,
    template_id=template["id"],
    fields={
        "word": {"id": "word", "value": "ephemeral"},
        "definition": {"id": "definition", "value": "Lasting for a very short time; temporary"},
        "example": {"id": "example", "value": "The beauty of cherry blossoms is ephemeral."}
    }
)
```

**Batch creation with error handling:**
```python
results = {"success": [], "failed": []}

for question, answer in cards:
    try:
        card = api.create_card(
            content=f"# {question}\n---\n{answer}",
            deck_id=deck_id,
            manual_tags=tags
        )
        results["success"].append(card["id"])
    except MochiAPIError as e:
        results["failed"].append({"question": question, "error": str(e)})
```

### Step 4: Report Results

Report to the user:
- Number of cards created successfully
- Any failures with specific error details
- Deck and tag organization summary

### Human Checkpoint: Offer Iteration

After reporting results, offer refinement:

- "I've created N cards covering [lenses/types]. Would you like me to add more?"
- "Any of these feel too difficult? I can add mnemonic cues."
- "Should I create salience prompts to help you apply this in your work?"
- "Want to review the cards in Mochi before we continue?"

## Output

Cards are created directly in the user's Mochi.cards account via the API. The deliverable is:

- **Flashcards** in the specified deck, tagged and organized
- **Decks/subdecks** created as needed for organization
- **Templates** created if structured card formats were used

### Card Content Format

Cards use markdown with `---` to separate sides:
```markdown
# Question text
---
Answer text with **formatting**
```

### Deck Organization

Use hierarchical structures: Subject → Topic → Subtopic
```python
parent = api.create_deck(name="Programming")
child = api.create_deck(name="Python", parent_id=parent["id"])
```

### Additional API Operations

**Soft delete** (preferred, reversible):
```python
from datetime import datetime
api.update_card(card_id, trashed=datetime.utcnow().isoformat())
```

**Pagination** for large collections:
```python
result = api.list_cards(deck_id=deck_id, limit=100)
if result.get("bookmark"):
    next_page = api.list_cards(deck_id=deck_id, limit=100, bookmark=result["bookmark"])
```

For complete API details, field types, and edge cases, consult:

→ **`references/mochi_api_reference.md`**
