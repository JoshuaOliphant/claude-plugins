# Knowledge Retrieval: Batch CSV Import Skill for mochi-creator

La Boeuf, here's what I found from our institutional memory before you start building.

## Search Summary

- **Knowledge bases searched**: claude-plugins local (3 solutions), second-brain cross-project (379 solutions)
- **Grep queries**: 7 parallel searches across project names, components (plugin/skill/api), tags (batch/csv/import/plugin/skill/pattern)
- **Semantic search**: vault-recommender on second-brain (5 results, top score 0.384)
- **Critical patterns checked**: `critical-patterns.md` in second-brain -- reviewed, none apply to this task (all relate to Kubernetes secrets, Docker security scans, AWS cross-account, Fastlane/iOS)
- **Stored feedback**: No feedback entries found for compound-knowledge
- **Total candidates evaluated**: 32 files; 9 fully read

## No Direct Matches for "Batch CSV Import"

No past solutions exist for CSV parsing, batch imports, or bulk card creation. This is genuinely new territory for the codebase. That said, several patterns and principles from past work directly inform how you should build it.

---

## Relevant Principles

### 1. Skill Value Correlates with Knowledge Specificity (High Relevance)

**Why this applies**: A batch CSV import skill would teach Claude how to parse CSV files into Mochi card format, handle the Mochi API's field naming conventions (kebab-case, boolean `?` suffixes), and manage pagination/rate-limiting on bulk creates. Claude doesn't know any of this natively -- this is exactly the high-value skill type (tool-specific knowledge) that produces the biggest eval deltas.

**Recommendation**: Focus the skill on Mochi-specific knowledge -- field mapping from CSV columns to Mochi card fields, template assignment, deck routing -- rather than generic CSV parsing (which Claude already handles well).

> File: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/skill-value-correlates-with-knowledge-specificity-claude-plugins-20260304.md`

### 2. Skill Descriptions Must Be Trigger-Only (High Relevance)

**Why this applies**: When you write the SKILL.md description for the batch import skill, do NOT summarize the workflow ("parses CSV, maps columns, creates cards in batches of 100"). Instead, write only triggering conditions ("Use when importing cards from CSV, spreadsheet, or bulk data into Mochi decks").

**The anti-pattern**: Descriptions that summarize workflow cause Claude to shortcut the skill body -- it reads the description, thinks it knows what to do, and never invokes the full skill.

> File: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/skill-descriptions-trigger-only-claude-plugins-20260302.md`

### 3. Native API Over Wrappers / Leverage SDK Patterns (Medium Relevance)

**Why this applies**: The existing `mochi_api.py` client is a thin wrapper around the Mochi REST API. For batch operations, you'll need to decide whether to add batch methods to the existing client or build a separate batch layer. The principle says: keep the integration layer thin and use the API's native patterns (pagination via `bookmark`, rate limits) rather than building elaborate abstractions.

**Recommendation**: Add a `create_cards_batch()` method to the existing `MochiAPI` class that handles chunking and error recovery, rather than building a separate orchestration layer.

> Files: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/integration/native-async-api-over-wrapper-ragamuffin-20260122.md`, `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/leverage-sdk-native-patterns-ragamuffin-20260122.md`

---

## Relevant Patterns

### 4. Multi-Modal Skill Ecosystem (Medium Relevance)

**Why this applies**: The mochi-creator plugin currently has one skill. Adding a batch import skill creates a two-skill plugin. The multi-modal ecosystem pattern says: when skills serve different interaction modes (interactive card creation vs. bulk import), give each skill its own SKILL.md with distinct trigger conditions, but share the same `references/` directory and API client.

**Recommendation**: Create `skills/mochi-batch-import/SKILL.md` as a sibling to `skills/mochi-creator/SKILL.md`. Both should use the same `mochi_api.py` script -- don't duplicate the API client.

> File: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/multi-modal-skill-ecosystem-marketplace-20260304.md`

### 5. Multi-Agent Pipeline: Deterministic Scripts + LLM Intelligence (Medium Relevance)

**Why this applies**: Batch CSV import has both deterministic parts (parsing CSV, validating columns, chunking rows) and LLM-intelligent parts (mapping ambiguous column names to Mochi fields, generating card content from raw data). The resume-tailor pipeline pattern splits these cleanly.

**Recommendation**: Build the CSV parsing and validation as a Python script (deterministic, no LLM tokens wasted). Let the SKILL.md orchestrate the LLM-intelligent parts (column mapping, content formatting decisions).

> File: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/multi-agent-plugin-pipeline-resume-tailor-20260314.md`

### 6. Generic Feedback Persistence (Low Relevance, but worth knowing)

**Why this applies**: If users will repeatedly correct how the batch import handles column mapping or formatting, consider adding feedback support from day one. The pattern is already implemented in the plugin ecosystem -- a single `feedback_manager.py` script handles storage for any plugin.

> File: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/generic-feedback-persistence-plugin-ecosystem-claude-plugins-20260316.md`

### 7. Plugin Modernization: Declarative over Imperative (Low Relevance)

**Why this applies**: When building the new skill, use Claude Code v2.1+ native features (declarative frontmatter for `allowed-tools`, etc.) rather than scripting behaviors manually. The plugin was recently modernized to use native worktree isolation and task management.

> File: `knowledge/solutions/patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md`

---

## Actionable Recommendations

1. **Structure**: Create `plugins/mochi-creator/skills/mochi-batch-import/` with its own `SKILL.md` and a `scripts/csv_importer.py` for deterministic CSV parsing
2. **API Client**: Extend the existing `mochi_api.py` with a `create_cards_batch()` method rather than building a separate client
3. **Skill Focus**: Encode Mochi-specific knowledge (field naming conventions, template mapping, deck routing) -- not generic CSV parsing
4. **Description**: Write trigger-only ("Use when importing cards from CSV files or spreadsheets into Mochi decks")
5. **Script/Skill Split**: CSV parsing and validation in Python script; column-to-field mapping intelligence in SKILL.md
6. **Dogfood**: After building, test by importing real flashcards from a CSV, not just synthetic test data

## Knowledge Gap Noted

There is no existing solution for "batch API operations with error recovery and partial failure handling." If the batch import implementation discovers patterns around retry logic, partial success reporting, or idempotent batch creates, that would be a good candidate for `compound-capture` afterward.
