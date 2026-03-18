La Boeuf, good news -- we have a well-documented pattern for exactly this.

## Search Summary

- **Knowledge bases searched**: second-brain (379 solutions), claude-plugins (3 solutions)
- **Search method**: Grep on frontmatter tags (feedback, persist, storage, config, plugin) + full-text (feedback.persist, feedback.manager)
- **Candidates found**: 5 files across both KBs; 3 directly relevant, read in full
- **Critical patterns checked**: `critical-patterns.md` reviewed -- no patterns apply to this task (all 6 entries are infrastructure/CI-related)
- **Cross-project registry**: Consulted; both registered KBs were searched

## The Recommended Pattern

There is a documented architecture specifically for this: **Generic Feedback Persistence for Plugin Ecosystems**.

**Source**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/generic-feedback-persistence-plugin-ecosystem-claude-plugins-20260316.md`

### Three-Layer Architecture

| Layer | What | Where | Your Responsibility |
|-------|------|-------|---------------------|
| **Storage** | `feedback_manager.py` | `${PLUGIN_ROOT}/scripts/` | Copy the existing generic script -- it is parameterized by plugin name and requires zero customization |
| **Semantics** | `skills/feedback/SKILL.md` | Your plugin's skills dir | Define your domain-specific categories (e.g., `output_format`, `quality_gates`, `general`) |
| **Consumption** | Step 0 in main SKILL.md | Each skill's Process section | Load feedback before starting work |

### How It Works

1. **Save feedback** -- accepts JSON on stdin, stores to `~/.claude/{plugin-name}/feedback.yaml`:
   ```bash
   echo '{"category": "metrics", "feedback": "Prefer precision over recall"}' | \
     python feedback_manager.py your-plugin save-feedback
   ```

2. **Show feedback** -- grouped by category, loaded at skill startup:
   ```bash
   python feedback_manager.py your-plugin show-feedback
   ```

3. **Clear feedback** -- all or by category:
   ```bash
   python feedback_manager.py your-plugin clear-feedback metrics
   ```

### Consumption Pattern

Add a Step 0 to each of your skills that should respect user preferences:

```markdown
### Step 0: Load Stored Feedback
python ${PLUGIN_ROOT}/scripts/feedback_manager.py {your-plugin} show-feedback
Apply relevant feedback to shape behavior.
```

### Consolidation Lifecycle

Feedback graduates from ephemeral to permanent:

```
User correction --> save --> runtime YAML (ephemeral)
                                  |
                      "consolidate feedback"
                                  |
                   Claude reads feedback + SKILL.md
                                  |
                   Proposes edits, user approves
                                  |
                   Baked into SKILL.md (permanent)
                   Graduated entries cleared
```

Entries are classified as **universal** (always apply, bake into SKILL.md) or **situational** (context-dependent, keep as runtime YAML).

### What to Do

1. **Copy `feedback_manager.py`** from the compound-knowledge plugin at `plugins/compound-knowledge/scripts/feedback_manager.py` into your plugin's `scripts/` directory. It is ~120 lines of stdlib Python with no dependencies.

2. **Define 5-8 domain-specific categories** in a feedback SKILL.md for your plugin. Keep them focused -- too many categories make classification ambiguous.

3. **Add Step 0** to each main skill that should respect stored preferences.

4. **Review periodically** and consolidate stable entries into SKILL.md to prevent feedback.yaml from growing unbounded.

### Key Design Decisions

- The script knows nothing about domain-specific categories -- semantics live in SKILL.md, storage is generic
- Storage location is `~/.claude/{plugin-name}/feedback.yaml` -- one file per plugin, entries separated by `---`
- Adding feedback to a new plugin takes about 15 minutes

## Related Knowledge

Two related patterns may also be useful depending on your plugin's complexity:

- **Two-tier source of truth with drift detection** (`patterns/two-tier-source-of-truth-resume-tailor-20260314.md`) -- if your plugin also needs human-editable markdown files that feed into scripts, this pattern addresses keeping them in sync.

- **Multi-agent plugin pipeline** (`patterns/multi-agent-plugin-pipeline-resume-tailor-20260314.md`) -- if your plugin uses multiple agents, the feedback pattern was originally designed within this architecture. The resume-tailor plugin originated the pattern.

## Gap Noted

There is no solution documenting how to **test** feedback persistence (e.g., verifying round-trip save/show/clear, category filtering). If you end up writing tests for this, that would be a good candidate for compound-capture afterward.
