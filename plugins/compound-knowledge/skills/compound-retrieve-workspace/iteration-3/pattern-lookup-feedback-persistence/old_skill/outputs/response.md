# Knowledge Base Results: Feedback Persistence Pattern

La Boeuf, good news -- we have a well-documented pattern for exactly this. Here is what the knowledge base surfaced.

---

## Direct Match: Generic Feedback Persistence Pattern

**File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/generic-feedback-persistence-plugin-ecosystem-claude-plugins-20260316.md`

This is the canonical solution. The recommended pattern uses a **three-layer architecture**:

| Layer | What | Where | Responsibility |
|-------|------|-------|----------------|
| **Storage** | `feedback_manager.py` | `${PLUGIN_ROOT}/scripts/` | Generic JSON-to-YAML persistence, parameterized by plugin name |
| **Semantics** | `skills/feedback/SKILL.md` | Per-plugin skill | Defines domain-specific categories, trigger phrases, examples |
| **Consumption** | Step 0 in main SKILL.md | Each skill's Process section | Loads feedback before starting work |

### How to set it up for your new plugin

1. **Copy `feedback_manager.py`** from any existing plugin (e.g., `plugins/autoloop/scripts/feedback_manager.py`) into your plugin's `scripts/` directory. The script is generic -- it takes the plugin name as the first CLI argument and knows nothing about your domain. It is ~120 lines, stdlib only, no dependencies.

2. **Create `skills/feedback/SKILL.md`** in your plugin. This is where you define your domain-specific categories. Keep it to 5-8 categories. For example, autoloop uses: `loop_design`, `metrics`, `quality_gates`, `runner_script`, `time_budget`, `change_strategy`, `general`. Pick categories that match the kinds of corrections users will give your plugin.

3. **Add Step 0 to your main skill(s)**. Before each skill's existing steps, add:
   ```markdown
   ### Step 0: Load Stored Feedback
   python ${PLUGIN_ROOT}/scripts/feedback_manager.py {your-plugin-name} show-feedback
   Apply relevant feedback to subsequent steps.
   ```

4. **Storage location**: Feedback is stored at `~/.claude/{plugin-name}/feedback.yaml`, one file per plugin, entries separated by `---`.

### CLI Interface

```bash
# Save feedback (reads JSON from stdin)
echo '{"category": "general", "feedback": "..."}' | \
  python feedback_manager.py your-plugin save-feedback

# Show all feedback grouped by category
python feedback_manager.py your-plugin show-feedback

# Clear all or by category
python feedback_manager.py your-plugin clear-feedback
python feedback_manager.py your-plugin clear-feedback some_category
```

### Consolidation Lifecycle

The pattern includes a graduation path so feedback.yaml does not grow unbounded:

```
User correction -> save -> runtime YAML (ephemeral)
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

Entries are classified as **Universal** (always apply -- edit SKILL.md, clear from YAML) or **Situational** (context-dependent -- keep as runtime YAML).

---

## Existing Implementations for Reference

Every plugin in the monorepo already has this set up. You can use any of these as a template:

- `plugins/autoloop/scripts/feedback_manager.py` + `plugins/autoloop/skills/feedback/SKILL.md`
- `plugins/autonomous-sdlc/scripts/feedback_manager.py` + `plugins/autonomous-sdlc/skills/feedback/SKILL.md`
- `plugins/compound-knowledge/scripts/feedback_manager.py` + `plugins/compound-knowledge/skills/feedback/SKILL.md`
- `plugins/hexagonal-agents/scripts/feedback_manager.py` + `plugins/hexagonal-agents/skills/feedback/SKILL.md`
- `plugins/mochi-creator/scripts/feedback_manager.py` + `plugins/mochi-creator/skills/feedback/SKILL.md`
- `plugins/resume-tailor/scripts/feedback_manager.py` + `plugins/resume-tailor/skills/feedback/SKILL.md`

---

## Related Principles

- **User Feedback Integration Loop** (`principles/user-feedback-integration-snc-mailscan-20260122.md`): Engage users early and incorporate feedback immediately -- users reveal requirements developers miss.
- **Skill Ecosystem Interconnection** (`patterns/skill-ecosystem-interconnection-audit-second-brain-20260315.md`): When your plugin grows past ~15 skills, audit for missing cross-delegation between feedback and other skills.

---

## Recommendation

The setup takes about 15 minutes: copy the script, write a feedback SKILL.md with your categories, add Step 0 to your main skills. Add feedback support from day one -- the solution file explicitly notes it is cheaper than retrofitting it later.

No critical patterns matched for this query.
