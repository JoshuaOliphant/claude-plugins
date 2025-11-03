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

### adw-bootstrap

**Version 1.0.0** - Bootstrap AI Developer Workflows (ADWs) infrastructure in any codebase enabling programmatic agent orchestration.

**What It Does:**
Transforms regular projects into ones where AI agents can be invoked programmatically to plan, implement, test, and deploy features. Uses intelligent adaptation to fit any project structure, language, or framework.

**Core Features:**
- **Programmatic Agent Execution**: Execute prompts via subprocess or SDK
- **Progressive Enhancement**: Three setup phases (Minimal → Enhanced → Scaled)
- **Intelligent Adaptation**: Analyzes target project and adapts patterns to fit conventions
- **Upgrade Support**: Safely upgrade existing setups to higher phases with automatic backups
- **Reusable Templates**: Slash command templates for common workflows
- **Multi-Phase Workflows**: Orchestrate plan → implement → test → deploy sequences
- **Structured Observability**: Agent outputs tracked in `agents/{id}/` directories
- **Three Model Support**: Haiku (fast), Sonnet (balanced), Opus (max intelligence)
- **Git Worktree Isolation**: Scaled phase includes isolated development environments
- **State Management**: Persistent state across workflow phases
- **GitHub Integration**: Issue tracking, PR creation, automated workflows

**Setup Phases:**

**Minimal** (Always installed):
- Core subprocess execution
- Basic CLI (`adw_prompt.py`)
- Essential slash commands (chore, implement)
- Structured output directories

**Enhanced** (Recommended for development):
- SDK-based execution with type safety
- Interactive session support
- Compound workflows (plan + implement in one command)
- Richer slash command library

**Scaled** (Production/teams):
- State management (`adw_state.json`)
- Git worktree isolation in `trees/` directories
- GitHub integration (gh CLI)
- Multi-phase SDLC workflows
- 20+ advanced slash commands

**Installation:**

```bash
# Add this marketplace
/plugin marketplace add joshuaoliphant/claude-plugins

# Install the plugin
/plugin install adw-bootstrap@oliphant-plugins
```

**Usage Examples:**

Bootstrap new projects:
- "Set up ADWs" → Analyzes project and creates appropriate infrastructure
- "Bootstrap agentic workflows" → Detects language, framework, and adapts setup
- "Initialize ADW infrastructure" → Recommends setup phase based on project maturity

Upgrade existing setups:
- "Upgrade my ADWs to enhanced" → Adds SDK support and compound workflows
- "Upgrade to scaled ADWs" → Adds state management and worktree isolation
- "Add scaled capabilities" → Safely adds features with automatic backups

After setup:
- `./adws/adw_prompt.py "implement feature X"` → Direct prompt execution
- `./adws/adw_prompt.py "quick check" --model haiku` → Fast economical execution
- `./adws/adw_chore_implement.py "add logging"` → Plan + implement workflow
- `./adws/adw_sdlc_iso.py 123` → Complete SDLC for issue #123 (scaled phase)

**Philosophy:**

The skill uses "intelligence over templating" - it reads working reference implementations, analyzes your project structure, and intelligently adapts patterns to fit your conventions. No rigid string substitution.

**Progressive Enhancement:**

Start minimal (5 files) and add capabilities as needed. Clean upgrade path with safety backups ensures you never lose customizations.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## License

MIT
