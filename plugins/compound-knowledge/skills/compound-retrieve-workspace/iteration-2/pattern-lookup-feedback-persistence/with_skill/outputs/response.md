# Knowledge Base Results: Feedback Persistence for Plugins

La Boeuf, good news -- we have a well-documented, battle-tested pattern for exactly this. It has been implemented across all 6 plugins in this repo already.

## No Critical Pattern Warnings

None of the critical patterns in the knowledge base apply to feedback persistence.

## Recommended Pattern: Generic Feedback Persistence (Three-Layer Architecture)

**Source**: `~/Dropbox/python_workspace/second_brain/knowledge/solutions/patterns/generic-feedback-persistence-plugin-ecosystem-claude-plugins-20260316.md`

The established pattern uses three layers:

| Layer | What | Where |
|-------|------|-------|
| **Storage** | `feedback_manager.py` | `${PLUGIN_ROOT}/scripts/` |
| **Semantics** | `skills/feedback/SKILL.md` | Per-plugin skill directory |
| **Consumption** | Step 0 in each main skill | Loads feedback before starting work |

### How It Works

1. **One generic script** (`feedback_manager.py`, ~150 lines, stdlib only) handles all persistence. It is parameterized by plugin name -- the script knows nothing about your domain. Storage location: `~/.claude/{plugin-name}/feedback.yaml`, YAML entries separated by `---`.

2. **Domain categories live in your feedback SKILL.md**, not in the script. You define 5-8 categories relevant to your plugin (e.g., autoloop uses `loop_design`, `metrics`, `quality_gates`, `runner_script`, `time_budget`, `change_strategy`, `general`).

3. **Each main skill adds a Step 0** that loads stored feedback before doing real work:
   ```bash
   python ${PLUGIN_ROOT}/scripts/feedback_manager.py {your-plugin} show-feedback
   ```

### CLI Interface

```bash
# Save feedback (JSON on stdin)
echo '{"category": "general", "feedback": "..."}' | \
  python feedback_manager.py your-plugin save-feedback

# Show all feedback grouped by category
python feedback_manager.py your-plugin show-feedback

# Clear all or by category
python feedback_manager.py your-plugin clear-feedback [category]
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

Universal preferences get baked into the SKILL.md. Situational/context-dependent preferences stay as runtime YAML.

## Implementation Checklist

Setting this up for a new plugin takes about 15 minutes:

1. **Copy `feedback_manager.py`** from any existing plugin's `scripts/` directory (they are all identical). For example:
   - `plugins/compound-knowledge/scripts/feedback_manager.py`
   - `plugins/autoloop/scripts/feedback_manager.py`

2. **Create `skills/feedback/SKILL.md`** defining your plugin-specific categories, trigger phrases, and examples. Use `plugins/autoloop/skills/feedback/SKILL.md` as a template.

3. **Add Step 0** to your main skill's process section to load feedback before work begins.

4. **Register the feedback skill** in your `plugin.json` skills list.

## Related Knowledge

- **Multi-agent plugin pipeline** (`patterns/multi-agent-plugin-pipeline-resume-tailor-20260314.md`): The resume-tailor architecture that originated this feedback pattern. If your plugin has a multi-phase pipeline, this shows how feedback integrates with parallel agent spawning.

- **Skill ecosystem interconnection** (`patterns/skill-ecosystem-interconnection-audit-second-brain-20260315.md`): When your plugin grows past ~15 skills, run an interconnection audit to ensure feedback is wired into all skills that need it, not just the main one.

## Existing Implementations (for Reference)

All 6 plugins in this repo already use this pattern. You can reference any of them:

- `plugins/autoloop/scripts/feedback_manager.py` + `plugins/autoloop/skills/feedback/SKILL.md`
- `plugins/compound-knowledge/scripts/feedback_manager.py` + `plugins/compound-knowledge/skills/feedback/SKILL.md`
- `plugins/autonomous-sdlc/scripts/feedback_manager.py` + `plugins/autonomous-sdlc/skills/feedback/SKILL.md`
- `plugins/hexagonal-agents/scripts/feedback_manager.py` + `plugins/hexagonal-agents/skills/feedback/SKILL.md`
- `plugins/mochi-creator/scripts/feedback_manager.py` + `plugins/mochi-creator/skills/feedback/SKILL.md`

## Gap Note

No gaps identified -- this is one of the most thoroughly documented patterns in the knowledge base, with both the architectural solution and concrete implementations available.
