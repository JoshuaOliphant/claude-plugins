## Search Context

- **Task**: Planning a new mochi-creator skill for batch CSV card imports
- **Keywords**: mochi, csv, batch, import, plugin, skill, api-client, design, architecture, feature-planning
- **Solutions Path**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/`
- **Registry**: 2 registered KBs (second-brain: 379 solutions, claude-plugins: 3 solutions)
- **Files Scanned**: 52 candidates across both knowledge bases

## Critical Patterns

Reviewed `critical-patterns.md` -- none of the 6 critical patterns (External Secrets, Container Base Images, Cross-Account AWS, Fastlane pricing, iOS screenshots, TestFlight build numbers) apply to this task. No critical warnings.

## Relevant Principles

### 1. Skill Value Correlates with Knowledge Specificity
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/skill-value-correlates-with-knowledge-specificity-claude-plugins-20260304.md`
- **Source KB**: second-brain (primary)
- **Statement**: "Skills that encode tool-specific knowledge or process discipline produce the highest eval deltas. Skills that teach general patterns Claude already knows produce the lowest deltas."
- **Confidence**: high
- **Relevance**: A batch CSV import skill should encode Mochi API-specific knowledge (card format, field naming conventions, pagination, template handling) rather than generic CSV parsing -- Claude already knows how to parse CSVs.

### 2. Skill Descriptions Must Contain Only Triggering Conditions
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/skill-descriptions-trigger-only-claude-plugins-20260302.md`
- **Source KB**: second-brain (primary)
- **Statement**: "Skill descriptions that summarize workflow cause Claude to shortcut the skill body. Descriptions must contain only triggering conditions, never what the skill does or how it works."
- **Confidence**: high
- **Relevance**: When writing the new skill's SKILL.md frontmatter, the description must start with "Use when..." and list triggering scenarios (e.g., "Use when importing flashcards from CSV, bulk creating cards, or migrating card collections"), never summarize the import workflow.

### 3. Encode Existing Vocabulary, Not Abstract Rules
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/encode-existing-vocabulary-not-abstract-rules-second-brain-20260307.md`
- **Source KB**: second-brain (primary)
- **Statement**: "The highest-value content in a skill is domain-specific vocabulary (tag lists, enum values, directory conventions) that Claude cannot infer."
- **Confidence**: high
- **Relevance**: The batch import skill should encode Mochi-specific vocabulary: the kebab-case field naming convention (`deck-id`, `template-id`), the `---` card side separator, boolean suffixes (`archived?`, `trashed?`), and the expected CSV column mappings to Mochi API fields.

### 4. Dogfood Before Finalizing API Surface
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/dogfood-before-finalizing-api-surface-brooklet-20260315.md`
- **Source KB**: second-brain (primary)
- **Statement**: "Build a real consumer before locking the producer API -- theoretical design decisions get corrected by practical use."
- **Confidence**: high
- **Relevance**: Before finalizing the CSV format and import API, try importing a real set of flashcards. The actual use case will reveal whether you need template support, tag columns, deck selection, or other features you might over- or under-design.

### 5. Phase Delivery, Not Feature Creep
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/phase-delivery-feature-creep-ragamuffin-20260122.md`
- **Source KB**: second-brain (primary)
- **Statement**: "Working system trumps perfect design. Define clear phase boundaries, resist feature creep, ship iteratively."
- **Confidence**: high
- **Relevance**: A batch import skill could easily bloat with features (template mapping, tag inference, duplicate detection, dry-run mode). Define a Phase 1 that handles simple question/answer CSV imports, then iterate.

## Relevant Solutions

### 1. YAML Folded String Breaks Regex Validators
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/configuration/yaml-folded-string-breaks-regex-validators-claude-plugins-20260303.md`
- **Source KB**: second-brain (primary)
- **Project**: claude-plugins | **Component**: claude-code
- **Relevance**: When writing the new skill's SKILL.md frontmatter, avoid using YAML's `>` folded string operator in the description field -- it triggers validation errors.
- **Key Insight**: Use inline (single-line) descriptions instead of YAML block scalar operators. The `quick_validate.py` script uses regex, not a YAML parser, so `>` appears as an angle bracket.
- **Severity**: medium

### 2. Multi-Modal Skill Ecosystem Pattern
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/multi-modal-skill-ecosystem-marketplace-20260304.md`
- **Source KB**: second-brain (primary)
- **Project**: marketplace | **Component**: claude-code
- **Relevance**: Consider whether the batch import skill should be a separate skill or folded into the existing mochi-creator skill. The pattern says split when you serve different intents (creating single cards vs. bulk importing).
- **Key Insight**: Split into companion skills when a single skill would need to serve both "I'm creating a card" and "I'm importing 200 cards from a CSV" intents. But for simpler skills (single topic, single mode), one SKILL.md with references is sufficient. Since mochi-creator already exists for single-card creation, a separate `mochi-batch-import` skill makes sense.
- **Severity**: medium

### 3. Plugin Modernization for Claude Code v2.1+
- **File**: `~/Dropbox/python_workspace/claude-plugins/knowledge/solutions/patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md`
- **Source KB**: claude-plugins (local)
- **Project**: claude-plugins | **Component**: claude-code-plugins
- **Relevance**: New skills should use v2.1+ declarative frontmatter features (native worktree isolation, permission modes) rather than manual orchestration patterns.
- **Key Insight**: When building the new skill, use current Claude Code v2.1+ conventions for agent frontmatter rather than patterns from older plugin code.
- **Severity**: medium

### 4. Dogfood Plugin on Its Own Codebase
- **File**: `~/Dropbox/python_workspace/claude-plugins/knowledge/solutions/principles/dogfood-plugin-on-own-codebase-20260317.md`
- **Source KB**: claude-plugins (local)
- **Project**: cross-project | **Component**: claude-code-plugins
- **Relevance**: Test the batch import skill by actually using it to import real flashcards, not just synthetic test data.
- **Key Insight**: The best test of a plugin is using it on real work. Import a real CSV of flashcards you actually want to study.
- **Severity**: medium

### 5. Use Official Plugin Install Flow
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/use-official-plugin-install-flow-claude-plugins-20260226.md`
- **Source KB**: second-brain (primary)
- **Project**: claude-plugins | **Component**: claude-code
- **Relevance**: After building the new skill, install it through the official `/plugin install` flow -- manual JSON edits create ghost installations.
- **Key Insight**: Manual edits to `installed_plugins.json` and cache directories create installations that appear present but don't load. Always use `/plugin install`.
- **Severity**: high

## Recommendations

La Boeuf, here is what I would suggest based on the knowledge search:

1. **Focus the skill on Mochi-specific knowledge, not CSV parsing.** Claude already knows how to read CSVs. The skill's value will come from encoding the Mochi API's card format (`---` separator for front/back), field naming conventions (kebab-case with `?` suffixes), pagination via bookmarks, and rate limiting considerations for bulk operations. (Principle: Skill value correlates with knowledge specificity)

2. **Write the SKILL.md description as trigger-only.** Use something like: `"Use when importing flashcards from CSV files, bulk creating Mochi cards, migrating card collections, or batch-processing card data."` Do not describe the import workflow in the description. Use inline format, not YAML `>` folded strings. (Principles: trigger-only descriptions + YAML validator gotcha)

3. **Make it a separate companion skill, not an addition to the existing mochi-creator skill.** The existing mochi-creator handles interactive single-card creation. Batch CSV import is a different intent with different workflow (file reading, validation, progress tracking, error recovery). The multi-modal skill ecosystem pattern supports this split. Name it something like `mochi-batch-import` within the mochi-creator plugin.

4. **Ship Phase 1 as simple question/answer CSV import**, then iterate. Phase 1: CSV with `front`, `back`, `tags` columns into a specified deck. Phase 2: template support, field mapping. Phase 3: duplicate detection, dry-run preview. Resist building all three phases at once. (Principle: Phase delivery, not feature creep)

5. **Dogfood with a real CSV before finalizing.** Prepare an actual set of flashcards you want to import (not synthetic test data) and run the import. This will reveal whether the CSV column names, error handling, and deck selection flow actually work for real use cases. (Principle: Dogfood before finalizing API surface)

6. **The existing `mochi_api.py` client already handles the hard parts.** It manages auth, kebab-case translation, pagination, and error handling. The batch import skill should build on top of it rather than reimplementing API interactions. Check whether `mochi_api.py` needs a `bulk_create_cards` method or if iterating `create_card` with error handling is sufficient.

7. **Install via `/plugin install` after building.** Do not manually edit plugin JSON files. (Principle: Use official plugin install flow)
