Hey La Boeuf, I checked the knowledge bases before you start building. Here is what I found.

## Search Context

- **Task**: Adding a new batch CSV import skill to the mochi-creator plugin
- **Keywords**: batch, csv, import, api, mochi, skill, plugin, plugin-architecture, testing, dogfooding
- **Solutions Path**: `knowledge/solutions/` (primary), `~/Dropbox/python_workspace/second_brain/knowledge/solutions/` (cross-project)
- **Registry**: 2 registered KBs (claude-plugins: 3 solutions, second-brain: 379 solutions)
- **Files Scanned**: 3 local + 29 cross-project candidates

## Critical Patterns

No `critical-patterns.md` file found. Nothing to flag here.

## Relevant Principles

### 1. Skill descriptions must contain only triggering conditions
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/skill-descriptions-trigger-only-claude-plugins-20260302.md`
- **Source KB**: second-brain
- **Statement**: "Skill descriptions that summarize workflow cause Claude to shortcut the skill body. Descriptions must contain only triggering conditions, never what the skill does or how it works."
- **Confidence**: high
- **Relevance**: When you write the SKILL.md for the batch import skill, the `description` field must only contain trigger phrases like "Use when importing cards from CSV files" -- never summarize the workflow steps or CSV parsing logic.

### 2. Skill value correlates with knowledge specificity, not pattern complexity
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/skill-value-correlates-with-knowledge-specificity-claude-plugins-20260304.md`
- **Source KB**: second-brain
- **Statement**: "Skills that encode tool-specific knowledge or process discipline produce the highest eval deltas. Skills that teach general patterns Claude already knows produce the lowest deltas."
- **Confidence**: high
- **Relevance**: A batch CSV import skill should focus on encoding Mochi API-specific knowledge (card content format with `---` separator, kebab-case field naming, template field mapping, pagination/bookmarks) rather than general CSV parsing, which Claude already knows how to do.

### 3. Dogfood before finalizing API surface
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/dogfood-before-finalizing-api-surface-brooklet-20260315.md`
- **Source KB**: second-brain
- **Statement**: "Build a real consumer before locking the producer API -- theoretical design decisions get corrected by practical use."
- **Confidence**: high
- **Relevance**: Before locking down the CSV format and skill interface, use it yourself to import a real batch of cards. Expect 1-2 design decisions to get reversed during that first real use.

### 4. Dogfood your plugin on its own codebase
- **File**: `knowledge/solutions/principles/dogfood-plugin-on-own-codebase-20260317.md`
- **Source KB**: claude-plugins (primary)
- **Statement**: "The best test of an orchestration plugin is to use it to orchestrate work on its own codebase. Dogfooding reveals integration gaps, incorrect assumptions, and UX issues that synthetic evals miss."
- **Confidence**: high
- **Relevance**: After building the batch import skill, test it with a real CSV import task -- do not rely solely on synthetic eval prompts.

### 5. API-first design
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/api-first-design-ragamuffin-20260122.md`
- **Source KB**: second-brain
- **Statement**: "Build all functionality through APIs before UI to ensure completeness and enable multiple consumers."
- **Confidence**: high
- **Relevance**: The batch import logic should work through the existing `mochi_api.py` module first. Make sure the Python API client supports everything the batch skill needs before writing the SKILL.md.

## Relevant Solutions

### 1. Modernizing Claude Code plugins for v2.1+ native features
- **File**: `knowledge/solutions/patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md`
- **Source KB**: claude-plugins (primary)
- **Project**: claude-plugins | **Component**: claude-code-plugins
- **Relevance**: Documents the current plugin structure and declarative frontmatter patterns you should follow for the new skill.
- **Key Insight**: Use declarative frontmatter (`allowed-tools`, `permissionMode`, etc.) rather than procedural instructions. The pattern "declarative over imperative" is the winning approach for Claude Code skills.
- **Severity**: medium

### 2. Generic feedback persistence for plugin ecosystems
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/generic-feedback-persistence-plugin-ecosystem-claude-plugins-20260316.md`
- **Source KB**: second-brain
- **Project**: claude-plugins | **Component**: claude-code
- **Relevance**: The mochi-creator plugin already has a `feedback_manager.py`. Your new batch import skill should define domain-specific feedback categories (e.g., preferred CSV column mappings, default deck selection) in the SKILL.md so user preferences persist across sessions.
- **Key Insight**: Define feedback categories in the skill frontmatter rather than building a bespoke preference system.
- **Severity**: medium

## Recommendations

1. **Focus the skill on Mochi-specific knowledge**: The highest-value content for the SKILL.md is encoding the Mochi card format (`---` separator, template field mapping, `deck-id` kebab-case conventions, pagination with bookmarks). Claude already knows how to parse CSV files -- the skill's value is in teaching it how to map CSV columns to Mochi's specific API structures.

2. **Extend `mochi_api.py` first**: Before writing the SKILL.md, add a `batch_create_cards()` method (or similar) to the existing API client. This keeps the API logic testable independently of Claude Code's skill system. The existing client already handles auth, kebab-case translation, and error handling.

3. **Write trigger-only descriptions**: When you write the skill's `description` field, use only trigger phrases: "Use when importing multiple flashcards from CSV files, batch creating cards, or converting spreadsheet data to Mochi decks." Do not summarize the CSV parsing workflow.

4. **Dogfood with a real CSV**: Before considering the skill done, import an actual batch of cards. The first real use will likely reveal issues with column mapping assumptions, error handling for malformed rows, and what the "right" CSV format actually looks like for different card types (simple vs. template-based).

5. **Consider soft delete for batch operations**: The existing knowledge documents that Mochi supports soft vs. hard delete. For a batch import that might create many cards, include an undo/rollback strategy using soft delete (`trashed` field) rather than hard delete.
