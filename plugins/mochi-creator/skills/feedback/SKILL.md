---
name: feedback
description: >
  Save flashcard creation feedback proactively. MUST trigger when the user corrects card output
  ("cards are too easy", "too many cards", "wrong difficulty", "bad formatting") or confirms good
  output ("these cards are great", "yes, like that"). Also trigger on explicit requests: "save this
  feedback", "show my feedback", "clear feedback", "card preferences", "mochi settings", "flashcard
  style", "consolidate feedback", "bake in my preferences". Feedback loaded automatically when
  creating new Mochi cards.
args:
  - name: action
    description: "Action to take: save, show, clear, or consolidate"
    required: false
user-invokable: true
---

# Mochi Creator Feedback Manager

Persist feedback about flashcard creation across sessions. Stored feedback is automatically
loaded when creating new Mochi cards, ensuring quality and style preferences carry forward.

## Actions

### Save Feedback

When the user provides feedback on card creation, save it:

```bash
echo '{"category": "<category>", "feedback": "<what the user said>", "context": "<optional context>"}' | \
  python ${PLUGIN_ROOT}/scripts/feedback_manager.py mochi-creator save-feedback
```

**Categories**: card_quality, difficulty, formatting, deck_organization, topics, batch_size, general

**Examples**:
- "Cards are too easy, make them harder" → `{"category": "difficulty", "feedback": "Increase difficulty — require deeper recall, avoid questions answerable by surface-level recognition"}`
- "Use cloze deletions more often" → `{"category": "formatting", "feedback": "Prefer cloze deletion format over Q&A for factual knowledge cards"}`
- "Don't create more than 10 cards at a time" → `{"category": "batch_size", "feedback": "Limit batch creation to 10 cards maximum — easier to review and approve"}`
- "Always tag cards with the source topic" → `{"category": "deck_organization", "feedback": "Add a tag for the source material or topic on every card created"}`
- "Skip trivial definition cards" → `{"category": "card_quality", "feedback": "Don't create cards for basic definitions — focus on relationships, applications, and edge cases"}`
- "I'm studying for AWS certification" → `{"category": "topics", "feedback": "Current study focus is AWS certification — prioritize cloud architecture and AWS-specific concepts"}`

### Show Feedback

Display all stored feedback:

```bash
python ${PLUGIN_ROOT}/scripts/feedback_manager.py mochi-creator show-feedback
```

Present as a readable list grouped by category.

### Clear Feedback

Clear all feedback or feedback for a specific category:

```bash
# Clear all
python ${PLUGIN_ROOT}/scripts/feedback_manager.py mochi-creator clear-feedback

# Clear only difficulty feedback
python ${PLUGIN_ROOT}/scripts/feedback_manager.py mochi-creator clear-feedback difficulty
```

### Consolidate Feedback

Graduate stable feedback into the actual SKILL.md files, making corrections permanent. This is a
Claude-driven operation — no script needed.

**When to consolidate**: When the user says "update the plugin based on feedback", "consolidate feedback",
"bake in my preferences", or "graduate feedback into the skill".

**Process**:

1. Load all stored feedback:
```bash
python ${PLUGIN_ROOT}/scripts/feedback_manager.py mochi-creator show-feedback
```

2. Read the target SKILL.md file:
   - `${PLUGIN_ROOT}/skills/mochi-creator/SKILL.md`

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
   python ${PLUGIN_ROOT}/scripts/feedback_manager.py mochi-creator clear-feedback <category>
   ```
   - Keep non-graduated entries untouched

6. Report what changed and what remains as runtime feedback.

## How Feedback is Used

When mochi-creator creates new cards, it loads all feedback entries and applies them:

- **card_quality** feedback → adjusts the bar for what cards get created (focused, effortful)
- **difficulty** feedback → calibrates tractability — how challenging cards should be
- **formatting** feedback → shapes card format (Q&A vs cloze, markdown style, separators)
- **deck_organization** feedback → guides deck/subdeck structure and tagging conventions
- **topics** feedback → informs current study focus and priority areas
- **batch_size** feedback → limits how many cards are created per session
- **general** feedback → applied to all aspects of card creation

This ensures the user never has to repeat the same preference twice.
