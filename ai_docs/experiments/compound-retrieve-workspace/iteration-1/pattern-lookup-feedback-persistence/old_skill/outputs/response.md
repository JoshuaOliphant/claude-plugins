# Knowledge Base Results: Feedback Persistence Pattern

La Boeuf, good news -- we have a well-documented pattern for exactly this. Here is what the knowledge base turned up.

---

## Direct Hit: Generic Feedback Persistence Pattern

**File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/generic-feedback-persistence-plugin-ecosystem-claude-plugins-20260316.md`

This is the recommended pattern. It was extracted from the resume-tailor plugin (which built feedback persistence first) and generalized for the entire plugin ecosystem. Here is the architecture:

### Three-Layer Architecture

| Layer | What | Where | Responsibility |
|-------|------|-------|----------------|
| **Storage** | `feedback_manager.py` | `${PLUGIN_ROOT}/scripts/` | Generic JSON-to-YAML persistence, parameterized by plugin name |
| **Semantics** | `skills/feedback/SKILL.md` | Per-plugin skill | Defines domain-specific categories, trigger phrases, examples |
| **Consumption** | Step 0 in main SKILL.md | Each skill's Process section | Loads feedback before starting work |

### How It Works

1. **One generic script** (`feedback_manager.py`, ~120 lines, stdlib only) handles save/show/clear for any plugin. The plugin name is passed as the first CLI argument -- the script knows nothing about domain-specific categories.

2. **Storage location**: `~/.claude/{plugin-name}/feedback.yaml` (one file per plugin, entries separated by `---`).

3. **CLI interface**:
   ```bash
   # Save feedback (JSON on stdin)
   echo '{"category": "metrics", "feedback": "..."}' | \
     python feedback_manager.py your-plugin save-feedback

   # Show all stored feedback, grouped by category
   python feedback_manager.py your-plugin show-feedback

   # Clear all or by category
   python feedback_manager.py your-plugin clear-feedback metrics
   ```

4. **Domain categories** live exclusively in the feedback SKILL.md, not in the script. This separates storage (generic) from semantics (plugin-specific). Keep categories focused -- 5 to 8 per plugin. Too many makes classification ambiguous.

5. **Consumption**: Each main skill adds a "Step 0: Load Stored Feedback" before its existing steps:
   ```markdown
   ### Step 0: Load Stored Feedback
   python ${PLUGIN_ROOT}/scripts/feedback_manager.py {plugin} show-feedback
   Apply relevant feedback entries to the current task.
   ```

### Consolidation Lifecycle

Feedback has a graduation path from ephemeral to permanent:

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

The consolidate action classifies each entry as:
- **Universal** (always apply) -- edit SKILL.md, clear from YAML
- **Situational** (context-dependent) -- keep as runtime YAML

### Setup Time

Adding feedback to a new plugin takes approximately 15 minutes:
1. Copy `feedback_manager.py` to your plugin's `scripts/` directory
2. Write a feedback SKILL.md with your domain-specific categories
3. Add Step 0 to each main skill that should respect user preferences

---

## Supporting Principle: User Feedback Integration

**File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/principles/user-feedback-integration-snc-mailscan-20260122.md`

Core insight: "Engage users early and incorporate feedback immediately. Users reveal requirements developers miss." This principle supports adding feedback persistence from day one -- it is cheaper than building it later.

---

## Related Pattern: Context Loss Between Sessions

**File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/workflow/context-loss-between-sessions-general-20251220.md`

Feedback persistence is one layer in the broader problem of session-to-session context continuity. The four-tier knowledge system (core context, sliding window, consolidated knowledge, CLAUDE.md) complements the feedback pattern by addressing different temporal needs.

---

## Related Pattern: Skill Ecosystem Interconnection

**File**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/skill-ecosystem-interconnection-audit-second-brain-20260315.md`

When your plugin grows beyond ~15 skills, audit for missing cross-delegation. The feedback skill should be wired into every skill that accepts user corrections -- this is easy to miss when skills are added independently.

---

## Recommendations

1. **Copy the existing `feedback_manager.py`** from any plugin that already has it (e.g., compound-knowledge at `${PLUGIN_ROOT}/scripts/feedback_manager.py`). Do not build your own -- the generic script handles all plugins.

2. **Define 5-8 domain categories** in a `skills/feedback/SKILL.md` specific to your plugin. Think about what kinds of corrections users will give (output format, content preferences, quality thresholds, etc.).

3. **Add Step 0 to every skill** that should respect user preferences. This is a single line that loads and applies stored feedback before the skill begins its work.

4. **Plan for consolidation** from the start. Periodically review stored feedback and graduate stable, universal entries into permanent SKILL.md edits.

No critical patterns matched this query.
