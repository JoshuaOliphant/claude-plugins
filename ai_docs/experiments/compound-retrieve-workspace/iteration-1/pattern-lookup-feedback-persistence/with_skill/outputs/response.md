# Knowledge Retrieval: Feedback Persistence Pattern

## Search Context

- **Task**: Set up feedback persistence for a new plugin
- **Keywords**: feedback, persistence, preferences, plugin, storage, categories, consolidation
- **Solutions Path**: `knowledge/solutions/`
- **Registry**: 2 registered KBs (claude-plugins, second-brain)
- **Files Scanned**: 6 candidates across 2 knowledge bases

## Critical Patterns

No `critical-patterns.md` file found. No critical warnings to surface.

## Relevant Principles

### 1. Dogfood your plugin on its own codebase
- **File**: `knowledge/solutions/principles/dogfood-plugin-on-own-codebase-20260317.md`
- **Source KB**: claude-plugins (primary)
- **Statement**: "The best test of an orchestration plugin is to use it to orchestrate work on its own codebase."
- **Confidence**: high
- **Relevance**: After adding feedback persistence, test it by using your plugin to do real work and capturing actual corrections -- synthetic tests miss integration gaps.

## Relevant Solutions

### 1. Generic feedback persistence for plugin ecosystems (DIRECT HIT)
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/generic-feedback-persistence-plugin-ecosystem-claude-plugins-20260316.md`
- **Source KB**: second-brain (cross-project)
- **Project**: claude-plugins | **Component**: claude-code
- **Relevance**: This is exactly the pattern you're looking for -- it documents the recommended three-layer architecture for feedback persistence across all plugins.
- **Key Insight**: The pattern separates **storage** (a generic `feedback_manager.py` script parameterized by plugin name) from **semantics** (domain-specific categories defined in each plugin's `skills/feedback/SKILL.md`) from **consumption** (a "Step 0" in each main skill that loads feedback before starting work). This separation means adding feedback to a new plugin takes roughly 15 minutes.
- **Severity**: medium

### 2. Skill ecosystem interconnection audit
- **File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/skill-ecosystem-interconnection-audit-second-brain-20260315.md`
- **Source KB**: second-brain (cross-project)
- **Project**: second-brain | **Component**: claude-code
- **Relevance**: When adding feedback persistence, audit existing skills to ensure they all consume it -- skills added independently often miss cross-delegation.
- **Key Insight**: Skill ecosystems grow organically and accumulate missing interconnections. When adding a cross-cutting concern like feedback, check every skill in the plugin to wire up consumption.
- **Severity**: medium

## Cross-Project Results

The primary knowledge base (claude-plugins) had 0 direct matches for "feedback persistence" as a pattern. The definitive solution was found in the **second-brain** knowledge base, which contains the canonical write-up of this pattern.

## Recommendations

La Boeuf, here is the recommended setup for your new plugin:

### Step 1: Copy the generic script
Copy `plugins/compound-knowledge/scripts/feedback_manager.py` into your plugin's `scripts/` directory. **Do not modify it** -- it is intentionally generic and parameterized by plugin name.

### Step 2: Create a feedback SKILL.md
Create `skills/feedback/SKILL.md` in your plugin. Define your domain-specific categories (aim for 5-8). Use `plugins/compound-knowledge/skills/feedback/SKILL.md` as a template. The key sections are:
- **Categories** relevant to your plugin's domain
- **Save/Show/Clear** actions (same CLI interface, just change the plugin name)
- **Consolidate** action for graduating stable feedback into permanent SKILL.md edits

### Step 3: Add Step 0 to your main skills
Every skill that should respect user preferences needs a "Step 0" at the top of its process:

```bash
python ${PLUGIN_ROOT}/scripts/feedback_manager.py your-plugin-name show-feedback
```

Then apply the relevant categories before starting work.

### Step 4: Wire up the CLI
The script uses this interface:
```bash
# Save (pipe JSON to stdin)
echo '{"category": "general", "feedback": "..."}' | python feedback_manager.py your-plugin save-feedback

# Show all feedback
python feedback_manager.py your-plugin show-feedback

# Clear (all or by category)
python feedback_manager.py your-plugin clear-feedback [category]
```

Storage location: `~/.claude/{plugin-name}/feedback.yaml`

### Warning
Keep categories focused. The solution file specifically warns: "too many categories make classification ambiguous." The compound-knowledge plugin uses 7 categories as a good reference point.

### Gap noted
There is no solution in either knowledge base covering **feedback migration between plugin versions** -- if your plugin's categories change, existing feedback entries may become orphaned. This might be worth a compound-capture after you've built it out.
