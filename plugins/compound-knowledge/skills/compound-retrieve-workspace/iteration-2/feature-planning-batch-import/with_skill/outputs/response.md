# Knowledge Retrieval: Batch CSV Import Skill for mochi-creator

La Boeuf, I checked institutional knowledge before you start building. Here is what I found.

## Search Context

- **Task**: Adding a new skill to mochi-creator for batch card imports from CSV files
- **Keywords**: csv, batch, import, mochi, plugin, skill, api, cli, plugin-structure
- **Solutions Paths**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/` (primary, 379 solutions), `knowledge/solutions/` (local, 3 solutions)
- **Registry**: 2 registered KBs (second-brain, claude-plugins)
- **Files Scanned**: 41 candidates across both KBs

## Critical Patterns

None of the 6 critical patterns in `critical-patterns.md` apply to this task (they cover Kubernetes secrets, Docker security scans, AWS cross-account access, Fastlane pricing, iOS screenshots, and TestFlight build numbers).

## Relevant Principles

### 1. Skill descriptions must contain only triggering conditions
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/skill-descriptions-trigger-only-claude-plugins-20260302.md`
- **Source KB**: second-brain (cross-project)
- **Statement**: "Skill descriptions that summarize workflow cause Claude to shortcut the skill body. Descriptions must contain only triggering conditions, never what the skill does or how it works."
- **Confidence**: high
- **Relevance**: When you write the SKILL.md frontmatter for the batch import skill, the description must say *when* to use it (e.g., "Use when the user has a CSV file of flashcards to import into Mochi"), not *how* it works. If you describe the CSV parsing workflow in the description, Claude will skip reading the full skill body.

### 2. Skill value correlates with knowledge specificity
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/skill-value-correlates-with-knowledge-specificity-claude-plugins-20260304.md`
- **Source KB**: second-brain (cross-project)
- **Statement**: "Skills that encode tool-specific knowledge or process discipline produce the highest eval deltas. Skills that teach general patterns Claude already knows produce the lowest deltas."
- **Confidence**: high
- **Relevance**: A batch CSV import skill will be high-value if it encodes Mochi API-specific knowledge Claude cannot know from training data -- things like the kebab-case field naming convention, the `---` card separator format, the pagination bookmark pattern, and rate limiting behavior. If the skill just teaches "how to parse CSV in Python," Claude already knows that and the delta will be low. Focus the skill on Mochi-specific mapping logic.

### 3. Dogfood your plugin on its own codebase
- **File**: `knowledge/solutions/principles/dogfood-plugin-on-own-codebase-20260317.md`
- **Source KB**: claude-plugins (local)
- **Statement**: "The best test of an orchestration plugin is to use it to orchestrate work on its own codebase."
- **Confidence**: high
- **Relevance**: Once the batch import skill is built, test it by importing real flashcard data, not synthetic test cases.

## Relevant Solutions

### 1. Multi-Modal Skill Ecosystem for Domain Skills
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/multi-modal-skill-ecosystem-marketplace-20260304.md`
- **Source KB**: second-brain (cross-project)
- **Project**: marketplace | **Component**: claude-code
- **Relevance**: The mochi-creator plugin already has a main skill for interactive card creation. A batch import skill is a different interaction mode (file processing vs. interactive creation), which is exactly the pattern this solution addresses.
- **Key Insight**: Split companion skills by interaction mode, not by topic. The batch import skill should be a sibling skill (e.g., `mochi-creator:batch-import`) that shares the same `references/` directory and `scripts/mochi_api.py` client. Each skill has its own trigger description targeting distinct user intent. The main skill handles "create a card about X," while the batch skill handles "import these cards from a file."
- **Severity**: medium

### 2. Generic Feedback Persistence for Plugin Ecosystems
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/generic-feedback-persistence-plugin-ecosystem-claude-plugins-20260316.md`
- **Source KB**: second-brain (cross-project)
- **Project**: claude-plugins | **Component**: claude-code
- **Relevance**: The mochi-creator plugin already has a `feedback_manager.py` and a `skills/feedback/SKILL.md`. If the batch import skill accepts user corrections (e.g., "always map the 'question' column to the front of the card"), those preferences should be stored via the existing feedback mechanism.
- **Key Insight**: Add batch-import-specific feedback categories (e.g., `csv_mapping`, `import_defaults`) to the feedback skill rather than building a separate preference system. The three-layer architecture (storage/semantics/consumption) already exists in mochi-creator.
- **Severity**: medium

### 3. YAML Folded String Breaks Regex Validators
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/configuration/yaml-folded-string-breaks-regex-validators-claude-plugins-20260303.md`
- **Source KB**: second-brain (cross-project)
- **Project**: claude-plugins | **Component**: claude-code
- **Relevance**: When writing the SKILL.md frontmatter for the new batch import skill, avoid using the YAML `>` folded string operator in the description field -- it triggers validation failures.
- **Key Insight**: Use a single-line inline description instead of YAML block scalar operators. This is a known gotcha in this codebase.
- **Severity**: medium

### 4. Modernizing Claude Code Plugins for v2.1+ Native Features
- **File**: `knowledge/solutions/patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md`
- **Source KB**: claude-plugins (local)
- **Project**: claude-plugins | **Component**: claude-code-plugins
- **Relevance**: If the batch import skill needs to spawn subagents or use worktree isolation, use the declarative frontmatter patterns (`isolation: "worktree"`, `permissionMode: "none"`) rather than scripting them manually.
- **Key Insight**: Prefer declarative frontmatter over imperative shell scripting for Claude Code infrastructure. The plugin ecosystem has already migrated away from manual worktree management.
- **Severity**: medium

### 5. Click Command Groups for CLI Organization
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/click-command-groups-adw-cli-20251204.md`
- **Source KB**: second-brain (cross-project)
- **Project**: adw_cli | **Component**: python-uv
- **Relevance**: If you extend `mochi_api.py` with batch import CLI commands, consider using Click command groups to keep the namespace organized (e.g., `mochi_api.py batch import-csv`, `mochi_api.py batch validate`).
- **Key Insight**: Related CLI commands should be grouped under a shared namespace rather than added as top-level commands, improving discoverability.
- **Severity**: low

## Recommendations

1. **Structure the new skill as `mochi-creator:batch-import`** -- a companion skill in `plugins/mochi-creator/skills/batch-import/SKILL.md` that shares the existing `scripts/mochi_api.py` and `references/` directory. This follows the multi-modal skill ecosystem pattern.

2. **Focus skill content on Mochi-specific mapping**, not CSV parsing. The highest-value content will be: how CSV columns map to Mochi's kebab-case API fields, how to handle the `---` separator for front/back card content, how template fields map, and how to handle pagination when importing large batches. Claude already knows how to parse CSVs.

3. **Write the SKILL.md description as trigger-only**: something like `"Use when the user wants to import flashcards from a CSV file, spreadsheet, or bulk data source into Mochi decks."` Do not describe the import process in the description.

4. **Avoid the YAML `>` folded string operator** in the skill frontmatter description. Use a single inline string.

5. **Add feedback categories** for batch import preferences (`csv_mapping`, `import_defaults`, `error_handling`) to the existing `skills/feedback/SKILL.md` rather than building a new preference system.

6. **Knowledge gap noted**: There is no existing solution covering Mochi API rate limiting or batch operation error handling. After building the batch import skill, consider capturing those patterns via `compound-capture` for future reference.
