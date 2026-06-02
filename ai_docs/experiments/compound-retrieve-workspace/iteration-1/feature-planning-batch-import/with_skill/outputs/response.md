Hey La Boeuf, good call checking before building. I searched the knowledge base and found several patterns and principles directly relevant to adding a batch CSV import skill to mochi-creator. Here is what came back.

---

## Search Context

- **Task**: Add a new batch CSV import skill to the mochi-creator plugin
- **Keywords**: mochi, batch, csv, import, skill, plugin, api, claude-plugins
- **Solutions Path**: ~/Dropbox/python_workspace/second_brain/knowledge/solutions/
- **Registry**: 2 registered KBs (second-brain: 379 solutions, claude-plugins: 3 solutions)
- **Files Scanned**: 19 frontmatter-filtered candidates across both KBs

## Critical Patterns

No critical patterns from `critical-patterns.md` apply directly to this task. The critical patterns are focused on Kubernetes secrets, Docker CVEs, AWS cross-account access, Fastlane pricing, and iOS screenshots -- none overlap with batch CSV import or Mochi API work.

## Relevant Principles

### 1. Skill descriptions must contain only triggering conditions
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/skill-descriptions-trigger-only-claude-plugins-20260302.md`
- **Source KB**: second-brain (primary)
- **Statement**: "Skill descriptions that summarize workflow cause Claude to shortcut the skill body. Descriptions must contain only triggering conditions, never what the skill does or how it works."
- **Confidence**: high
- **Relevance**: When you write the SKILL.md frontmatter for batch-import, the description field must say *when* to use it (e.g., "Use when the user has a CSV file of flashcards to import into Mochi"), not *what* it does (e.g., "Parses CSV files and calls Mochi API to create cards in bulk"). If you summarize the workflow in the description, Claude will think it already knows the skill and never invoke it.

### 2. Skill value correlates with knowledge specificity, not pattern complexity
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/skill-value-correlates-with-knowledge-specificity-claude-plugins-20260304.md`
- **Source KB**: second-brain (primary)
- **Statement**: "Skills that encode tool-specific knowledge or process discipline produce the highest eval deltas. Skills that teach general patterns Claude already knows produce the lowest deltas."
- **Confidence**: high
- **Relevance**: A batch-import skill should focus on encoding Mochi-specific knowledge that Claude cannot infer: the card content format (`# Question\n---\nAnswer`), the kebab-case field naming convention (`deck-id`, `template-id`), the pagination bookmark pattern, soft-delete vs hard-delete semantics, and the `MochiAPIError` exception handling. Claude already knows how to parse CSV files -- the skill's value is in the Mochi API specifics.

### 3. Encode existing vocabulary, not abstract rules
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/encode-existing-vocabulary-not-abstract-rules-second-brain-20260307.md`
- **Source KB**: second-brain (primary)
- **Statement**: "The highest-value content in a skill is domain-specific vocabulary (tag lists, enum values, directory conventions) that Claude cannot infer."
- **Confidence**: high
- **Relevance**: The batch-import skill should include concrete examples of correct CSV column mappings to Mochi API fields, the exact field naming translations (Python snake_case to Mochi kebab-case with `?` suffixes for booleans), and the template field structure. Abstract instructions like "map CSV columns to API fields" are less valuable than a concrete mapping table.

### 4. Hooks beat skills for autonomous agent behavior
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/hooks-beat-skills-for-autonomous-agent-behavior-second-brain-20260314.md`
- **Source KB**: second-brain (primary)
- **Statement**: "When an agent behavior must happen reliably, use system-level hooks instead of skills or MCP tools."
- **Confidence**: high
- **Relevance**: If batch import should trigger automatically (e.g., when a CSV file is detected in the conversation), consider a hook instead. If it is user-initiated (explicit "/mochi-batch-import" or similar), a skill is the right choice. Based on the task description, this sounds user-initiated, so a skill is appropriate.

## Relevant Solutions

### 1. Multi-Modal Skill Ecosystem for Domain Skills
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/multi-modal-skill-ecosystem-marketplace-20260304.md`
- **Source KB**: second-brain (primary)
- **Project**: marketplace | **Component**: claude-code
- **Relevance**: With batch-import, mochi-creator will have two skills -- the original card-creation skill and the new batch-import skill. This pattern describes how to split a domain into companion skills with distinct trigger descriptions.
- **Key Insight**: Each skill's description should target a distinct user intent. The existing mochi-creator skill handles interactive card creation; the new batch-import skill handles bulk operations from files. Their descriptions should clearly separate these intents so Claude triggers the right one.
- **Severity**: medium

### 2. YAML folded string operator triggers angle bracket validators
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/configuration/yaml-folded-string-breaks-regex-validators-claude-plugins-20260303.md`
- **Source KB**: second-brain (primary)
- **Project**: claude-plugins | **Component**: claude-code
- **Relevance**: When writing the SKILL.md frontmatter for the new skill, avoid using YAML's `>` (folded string) operator in the description field -- it will fail validation.
- **Key Insight**: Use an inline (single-line) description instead of YAML block scalar operators. The `quick_validate.py` script uses regex, not a YAML parser, so `>` gets flagged as an angle bracket.
- **Severity**: medium

### 3. Skill Ecosystem Interconnection Audit Pattern
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/skill-ecosystem-interconnection-audit-second-brain-20260315.md`
- **Source KB**: second-brain (primary)
- **Project**: second-brain | **Component**: claude-code
- **Relevance**: Adding a new skill to an existing plugin is a good time to check namespace consistency and cross-delegation between skills. The new batch-import skill should reference the existing mochi_api.py client rather than reimplementing API calls.
- **Key Insight**: Periodically audit skill ecosystems for missing cross-delegation and duplicated logic. The batch-import skill should reuse the existing `MochiAPI` class from `scripts/mochi_api.py`.
- **Severity**: medium

### 4. Plugin Modernization for Claude Code v2.1+
- **File**: `~/Dropbox/python_workspace/claude-plugins/knowledge/solutions/patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md`
- **Source KB**: claude-plugins
- **Project**: claude-plugins | **Component**: claude-code-plugins
- **Relevance**: If you are building against recent Claude Code versions, newer frontmatter features (declarative worktree isolation, task management with dependencies, permission modes) are available.
- **Key Insight**: Use declarative frontmatter features rather than manual orchestration patterns when building new skills.
- **Severity**: medium

## Recommendations

1. **Focus the skill on Mochi-specific vocabulary**: Include the card content format, field naming translations (snake_case to kebab-case), pagination bookmarks, error handling with `MochiAPIError`, and template field structures. Claude already knows CSV parsing -- the skill's value is in the Mochi API mapping.

2. **Reuse the existing `MochiAPI` class**: The batch-import skill should import from `scripts/mochi_api.py` rather than making raw HTTP calls. This keeps API logic in one place and inherits the existing auth pattern, error handling, and field naming translation.

3. **Write trigger-only descriptions**: The SKILL.md description should say something like "Use when the user wants to import flashcards from a CSV file, has a bulk set of cards to create, or mentions batch import into Mochi" -- not "Parses CSV files, maps columns to Mochi API fields, and creates cards in bulk with error handling."

4. **Use inline YAML descriptions**: Do not use the `>` folded string operator in the SKILL.md frontmatter -- it will fail `quick_validate.py`. Write the description as a single long line.

5. **Consider the multi-modal pattern**: With two skills under mochi-creator, make sure each skill's trigger description targets a distinct intent. Interactive card creation vs. bulk file import are naturally distinct, so this should be straightforward.

6. **Follow TDD**: Per your established practice, write tests for the CSV parsing and batch API call logic before implementing them. The existing `mochi_api.py` client pattern (both importable module and CLI tool) is a good model for the batch import script.

---

**Knowledge gap noted**: There are no existing solutions about Mochi API rate limiting, batch operation error recovery (partial failures), or CSV validation patterns. If you encounter these during implementation, they would be good candidates for `/compound-knowledge:capture`.
