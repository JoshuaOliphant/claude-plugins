# Claude Code Plugin Marketplace

A collection of Claude Code plugins for productivity and learning workflows.

## Available Plugins

### mochi-creator

**Version 1.1.0** - Create evidence-based spaced repetition flashcards using cognitive science principles from Andy Matuschak's research.

**What Makes This Different:**
This plugin doesn't just create flashcards—it applies research-backed principles to ensure cards actually work for long-term retention. Based on Andy Matuschak's extensive work on spaced repetition and retrieval practice.

**Core Features:**
- **Quality Validation**: Checks prompts against 5 properties (focused, precise, consistent, tractable, effortful)
- **Evidence-Based Design**: Applies cognitive science principles to every card
- **Knowledge-Type Workflows**: Specialized patterns for factual, conceptual, procedural, and salience prompts
- **Anti-Pattern Detection**: Identifies and fixes common mistakes (binary questions, unfocused prompts, vague language)
- **5 Conceptual Lenses**: Creates robust understanding through multiple angles (attributes, similarities, parts, causes, significance)
- **Procedural Patterns**: Focus on transitions, rationale, and timing instead of rote memorization
- **Interactive Creation**: Guided workflows with quality checks at every step
- **Template Support**: Build reusable card formats with custom fields
- **Deck Management**: Hierarchical organization and batch operations

**Requirements:**
- Mochi.cards account and API key
- Python with `requests` library

**Installation:**

```bash
# Add this marketplace
/plugin marketplace add joshuaoliphant/claude-plugins

# Install the plugin
/plugin install mochi-creator@oliphant-plugins
```

**Setup:**

Set your Mochi API key as an environment variable:
```bash
export MOCHI_API_KEY="your_api_key_here"
```

To get your API key:
1. Open Mochi.cards application
2. Navigate to Account Settings
3. Find the API Keys section
4. Generate a new API key

**Quick Start:**

Here's the simplest way to get started—create flashcards about a basic concept:

1. Set your API key: `export MOCHI_API_KEY="your_api_key_here"`
2. Invoke the plugin: "Create Mochi cards to help me understand what recursion is"
3. Get evidence-based flashcards: Cards appear in your Mochi deck with focused, atomic prompts

That's it! The plugin handles quality validation and cognitive science principles automatically.

**Usage Examples:**

Simple requests:
- "Create Mochi cards about dependency injection" → Creates 5-8 focused, atomic cards
- "Turn this conversation into flashcards" → Extracts key concepts with quality validation
- "Help me create flashcards for learning React hooks" → Interactive workflow with guidance

Advanced workflows:
- "Create conceptual cards for TDD using the 5 lenses approach" → Attributes, similarities, examples, causes, significance
- "Make procedural cards for git workflow focusing on transitions and rationale" → No rote steps, emphasis on understanding
- "Create factual cards from this recipe" → Breaks into atomic prompts automatically

Quality-focused:
- Claude will proactively validate prompts and suggest improvements
- Detects unfocused prompts: "This tests 3 details - let me split into separate cards"
- Identifies anti-patterns: "This is a binary question - let me rephrase as open-ended"
- Applies knowledge-type appropriate patterns automatically

**The "More Than You Think" Rule:**
The plugin encourages creating 3-5 focused cards instead of 1 comprehensive card. Each focused prompt takes only 10-30 seconds across an entire year of review, but creates much stronger, more reliable memories.

**Research Foundation:**

This plugin is built on cognitive science research including:
- **Retrieval Practice** (Roediger & Karpicke, 2006): Active recall strengthens memory more than passive review
- **Spacing Effect** (Ebbinghaus, 1885; Cepeda et al., 2006): Distributed practice beats massed practice
- **Elaborative Encoding** (Craik & Lockhart, 1972): Deeper processing creates stronger memories
- **Desirable Difficulties** (Bjork, 1994): Optimal learning occurs with moderate challenge
- Andy Matuschak's extensive work on prompt design and spaced repetition systems

The 5 properties framework, knowledge-type patterns, and quality validation are all grounded in this research to ensure cards that actually work for long-term retention.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## License

MIT
