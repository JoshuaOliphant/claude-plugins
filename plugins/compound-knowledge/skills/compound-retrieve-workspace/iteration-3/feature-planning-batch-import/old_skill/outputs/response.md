Hey La Boeuf, I checked the knowledge base before you start building. Here is what I found.

## Search Context

- **Task**: Adding a new skill to the mochi-creator plugin for batch CSV card imports
- **Keywords**: mochi, plugin, skill, csv, batch, import, card, api, architecture, design
- **Solutions Path**: `knowledge/solutions/`
- **Registry**: 2 registered KBs (claude-plugins, second-brain)
- **Files Scanned**: 3 local candidates, 8 cross-project candidates evaluated

## Relevant Principles

### 1. Skill descriptions must contain only triggering conditions
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/skill-descriptions-trigger-only-claude-plugins-20260302.md`
- **Source KB**: second-brain (cross-project)
- **Statement**: "Skill descriptions that summarize workflow cause Claude to shortcut the skill body. Descriptions must contain only triggering conditions, never what the skill does or how it works."
- **Confidence**: high
- **Relevance**: When writing the SKILL.md for the new batch-import skill, the description frontmatter must start with "Use when..." and list only triggering conditions -- never summarize the CSV parsing workflow or batch logic.

### 2. Skill value correlates with knowledge specificity, not pattern complexity
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/skill-value-correlates-with-knowledge-specificity-claude-plugins-20260304.md`
- **Source KB**: second-brain (cross-project)
- **Statement**: "Skills that encode tool-specific knowledge or process discipline produce the highest eval deltas. Skills that teach general patterns Claude already knows produce the lowest deltas."
- **Confidence**: high
- **Relevance**: A batch CSV import skill has high potential value because it encodes Mochi API-specific knowledge (kebab-case field naming, pagination, template field mapping) that Claude does not know from training data. Focus the skill on Mochi-specific API patterns rather than generic CSV parsing.

### 3. Dogfood your plugin on its own codebase
- **File**: `knowledge/solutions/principles/dogfood-plugin-on-own-codebase-20260317.md`
- **Source KB**: claude-plugins (primary)
- **Statement**: "The best test of an orchestration plugin is to use it to orchestrate work on its own codebase. Dogfooding reveals integration gaps, incorrect assumptions, and UX issues that synthetic evals miss."
- **Confidence**: high
- **Relevance**: After building the batch-import skill, test it by actually importing real cards from a CSV -- not just with synthetic test data.

### 4. Dogfood before finalizing API surface
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/dogfood-before-finalizing-api-surface-brooklet-20260315.md`
- **Source KB**: second-brain (cross-project)
- **Statement**: "Build a real consumer before locking the producer API -- theoretical design decisions get corrected by practical use."
- **Confidence**: high
- **Relevance**: Before locking down the CSV format and batch import API, use it on a real deck import. Expect 1-2 design decisions to get reversed during dogfooding (e.g., column naming, error handling strategy, template field mapping).

### 5. Phase Delivery, Not Feature Creep
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/phase-delivery-feature-creep-ragamuffin-20260122.md`
- **Source KB**: second-brain (cross-project)
- **Statement**: "Working system trumps perfect design. Define clear phase boundaries, resist feature creep, ship iteratively."
- **Confidence**: high
- **Relevance**: A batch CSV import skill could easily grow in scope (template support, validation rules, duplicate detection, progress reporting). Define a minimal Phase 1 (basic CSV to cards) and resist adding features until it works end-to-end.

## Relevant Solutions

### 1. Modernizing Claude Code plugins for v2.1+ native features
- **File**: `knowledge/solutions/patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md`
- **Source KB**: claude-plugins (primary)
- **Project**: claude-plugins | **Component**: claude-code-plugins
- **Relevance**: Documents the current plugin structure and declarative frontmatter patterns you should follow when adding a new skill.
- **Key Insight**: Use declarative frontmatter (`allowed-tools`, `description` with trigger-only wording) rather than procedural instructions. The plugin system has matured -- leverage native features like `isolation: worktree` if the batch import needs to work on files.
- **Severity**: medium

### 2. Generic feedback persistence for plugin ecosystems
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/generic-feedback-persistence-plugin-ecosystem-claude-plugins-20260316.md`
- **Source KB**: second-brain (cross-project)
- **Project**: claude-plugins | **Component**: claude-code
- **Relevance**: If users will repeatedly use the batch import skill with preferences (default deck, CSV column mappings), the feedback persistence pattern lets those preferences survive across sessions.
- **Key Insight**: Use the existing `feedback_manager.py` parameterized by plugin name rather than building a bespoke preference system. Define domain-specific categories in the new SKILL.md.
- **Severity**: medium

## Recommendations

1. **Focus the skill on Mochi-specific knowledge**: The highest-value content for this skill is the Mochi API field naming conventions (kebab-case, `?` boolean suffixes), the card content format (`# Question\n---\nAnswer`), template field mapping, and pagination for large imports. Claude already knows how to parse CSV files -- do not spend skill real estate teaching that.

2. **Write a trigger-only description**: Your SKILL.md description should be something like `"Use when importing cards from CSV files, bulk creating flashcards, or batch importing content into Mochi decks."` Do not describe the CSV parsing workflow in the description.

3. **Reuse the existing `mochi_api.py` client**: The client at `plugins/mochi-creator/skills/mochi-creator/scripts/mochi_api.py` already handles authentication, field name translation, pagination, and error handling. The batch import skill should call into it rather than reimplementing API access.

4. **Ship in phases**: Phase 1 should be basic CSV-to-cards (content column mapped to card markdown, deck specified by name or ID). Phase 2 can add template field mapping, tag columns, and validation. Resist adding duplicate detection, progress bars, or rollback until Phase 1 works.

5. **Dogfood with a real import**: Before finalizing the CSV column format, import a real deck (e.g., a set of programming flashcards) from CSV. Expect the column naming or error handling design to need adjustment after the first real use.

6. **Remember versioning**: After adding the new skill, bump the version in `plugins/mochi-creator/.claude-plugin/plugin.json` and copy that version into `marketplace.json`.
