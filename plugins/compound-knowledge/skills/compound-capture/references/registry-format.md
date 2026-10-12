# ABOUTME: Shared schema reference for the cross-project knowledge registry file.
# ABOUTME: Defines entry fields, update rules, and location for ~/.claude/compound-knowledge-registry.md.

# Registry Format Reference

The **compound knowledge registry** is a central file that tracks all knowledge bases on the machine, enabling cross-project solution search.

## Location

Always: `~/.claude/compound-knowledge-registry.md`

## File Structure

```markdown
# Compound Knowledge Registry

Central directory of all knowledge bases on this machine.
Updated automatically when solutions are captured or `/compound-knowledge:setup` is run.

## Registered Knowledge Bases

### {project-name}
- **path**: {absolute_path_to_solutions_directory}
- **last_updated**: {YYYY-MM-DD}
- **solution_count**: {integer}
- **primary_components**: [{comma-separated component list}]
```

## Entry Fields

| Field | Type | Description |
|-------|------|-------------|
| `project-name` | string | H3 heading, derived from the project directory name (lowercase, hyphens) |
| `path` | absolute path | Full path to the `knowledge/solutions/` directory. Use `~` expansion. |
| `last_updated` | YYYY-MM-DD | Date of the most recent capture or setup in this knowledge base |
| `solution_count` | integer | Total number of `.md` files in the solutions directory (excluding `critical-patterns.md`) |
| `primary_components` | list | Unique `component:` values extracted from solution file frontmatter |

## Update Rules

1. **Idempotent**: If an entry already exists for a given `path`, update it in-place. Never create duplicate entries for the same path.
2. **Append-only for new entries**: New knowledge bases are appended at the end of the "Registered Knowledge Bases" section.
3. **Path is the unique key**: Two entries with different project names but the same path are considered duplicates. Use the path to match.
4. **Component list**: Extract unique values by running `Grep(pattern="^component:", path="{solutions_path}", output_mode="content")` and deduplicating. Limit to the top 10 most frequent components.
5. **Solution count**: Count via `Glob(pattern="**/*.md", path="{solutions_path}")` and subtract 1 for `critical-patterns.md` if it exists.

## When to Update

| Event | Action |
|-------|--------|
| `/compound-knowledge:setup` | Create entry (or update if path exists) with count=0, components=[] |
| After solution capture | Update `last_updated`, `solution_count`, `primary_components` for the entry matching the current `{solutions_path}` |
| First retrieval from a path | Register if not already present (idempotent) |

## Creating the Registry File

If `~/.claude/compound-knowledge-registry.md` does not exist, create it with this header:

```markdown
# Compound Knowledge Registry

Central directory of all knowledge bases on this machine.
Updated automatically when solutions are captured or `/compound-knowledge:setup` is run.

## Registered Knowledge Bases
```

Then append the first entry.
