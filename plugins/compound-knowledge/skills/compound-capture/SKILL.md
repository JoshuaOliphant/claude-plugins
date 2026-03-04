---
name: compound-capture
description: >
  Use after solving non-trivial problems, completing debugging sessions,
  discovering reusable patterns, making architecture decisions, or when
  the user confirms something works ("that worked", "it's fixed", "problem solved").
  Also use when explicitly invoked via /compound-knowledge in capture context.
  This skill captures solved problems and engineering principles as structured
  YAML-frontmatter files for grep-based retrieval across sessions and projects.
allowed-tools: [Read, Write, Edit, Grep, Glob]
---

# Compound Capture

Capture solved problems and engineering principles as searchable solution files. Every capture creates a structured markdown file with YAML frontmatter that enables fast grep-based retrieval in future sessions.

## Path Resolution

Before any capture operation, resolve the solutions directory path.

**Check in this order (first match wins):**

1. **Project-level override**: Read `{project_root}/.claude/compound-knowledge.local.md` — extract `solutions_path` value
2. **User-level override**: Read `~/.claude/compound-knowledge.local.md` — extract `solutions_path` value
3. **Default**: `{project_root}/knowledge/solutions/`

**`.local.md` format:**
```markdown
# Compound Knowledge Settings
solutions_path: /absolute/path/to/knowledge/solutions/
```

Extract the path from the line starting with `solutions_path:`. Expand `~` to the user's home directory.

**Store the resolved path as `{solutions_path}` for all subsequent operations.**

If the resolved directory does not exist, inform the user:
> "Solutions directory not found at `{solutions_path}`. Run `/compound-knowledge:setup` to initialize it."

## Registry

A central registry at `~/.claude/compound-knowledge-registry.md` tracks all knowledge bases on the machine. This enables cross-project solution search.

See `references/registry-format.md` for the full schema and update rules.

---

## When to Capture

### Trigger Phrases
- "That worked" / "It's fixed" / "Problem solved"
- "Finally got it working"
- Explicit `/compound-knowledge` invocation
- Test suite going from red to green after debugging

### Triviality Filter

**Skip capture for:**
- Typos, syntax errors, missing imports
- One-line fixes with no investigation
- Obvious bugs caught immediately

**Proceed with capture for:**
- Problems requiring multiple investigation attempts
- Non-obvious root causes
- Solutions involving code examples or architecture decisions
- Issues likely to recur in other contexts

## Principles vs Solutions

Determine whether you're recording a **solution** (specific problem fix) or a **principle** (generalizable engineering wisdom).

### Solutions
- Have `symptoms` (required) — observable errors or behaviors
- Live in category directories (`debugging/`, `patterns/`, etc.)
- Document a specific problem and its fix
- Use `problem_type` matching the category

### Principles
- Have `statement` (required) — a concise, generalizable rule
- Have `confidence` (required) — high, medium, or low
- Do **NOT** have `symptoms`
- Live in `principles/` directory
- Use `problem_type: principles`
- Document wisdom extracted from experience across projects

**Decision heuristic**: If someone could grep for an error message and find this, it's a solution. If it's advice that applies across many situations, it's a principle.

---

## Capture Workflow (9 Steps)

### Step 1: Resolve Solutions Path

Follow the Path Resolution algorithm above. Store the result as `{solutions_path}`.

### Step 2: Detect Confirmation

Apply the Triviality Filter (above). If the problem is trivial, skip capture.

If unsure whether the problem warrants capture, ask:
> "This seems like a solution worth documenting. Want me to capture it?"

### Step 3: Gather Context

Determine whether this is a **solution** or a **principle** (see "Principles vs Solutions" above).

**For solutions**, extract from the conversation:

| Field | Source | Required? |
|-------|--------|-----------|
| `title` | Problem description | Yes |
| `date` | Current date (auto-populated as YYYY-MM-DD) | Yes |
| `project` | Current working directory or explicit mention | Yes |
| `problem_type` | Nature of issue (see yaml-schema.md) | Yes |
| `component` | Technology involved | Yes |
| `symptoms` | Error messages, observable behavior | Yes |
| `solution_summary` | One-line fix description | Yes |
| `severity` | Impact assessment | Yes |
| `root_cause` | Why it happened | No |
| `resolution_type` | Type of fix applied | No |
| `tags` | Searchable keywords | No |
| `environment` | Runtime context | No |

If critical fields (title, project, component, symptoms) are missing, ask and wait:
> "I need a few details to capture this properly: What project is this for? What were the symptoms?"

**For principles**, extract from the conversation:

| Field | Source | Required? |
|-------|--------|-----------|
| `title` | Principle name | Yes |
| `date` | Current date (auto-populated as YYYY-MM-DD) | Yes |
| `project` | Where validated or "cross-project" | Yes |
| `problem_type` | Always `principles` | Yes |
| `component` | Technology domain | Yes |
| `statement` | Concise, generalizable rule (1-2 sentences) | Yes |
| `confidence` | high, medium, or low | Yes |
| `solution_summary` | One-line description of the principle | Yes |
| `severity` | Impact if ignored | Yes |
| `tags` | Searchable keywords | No |

If critical fields (title, statement, confidence) are missing, ask and wait:
> "I need a few details to capture this principle: What's the core statement? How confident are we?"

### Step 4: Check Existing Solutions

Search `{solutions_path}` for similar issues:

```
Grep(pattern="symptoms:.*{key_symptom}", path="{solutions_path}", output_mode="files_with_matches")
Grep(pattern="title:.*{similar_term}", path="{solutions_path}", output_mode="files_with_matches")
```

If a similar solution exists:
1. **Different root cause** → Create new file, add `related_solutions` cross-reference
2. **Same issue, new context** → Update existing file with additional context
3. **Exact duplicate** → Skip, inform user: "This is already documented in [file]"

### Step 5: Generate Filename

Format: `{sanitized-symptom}-{project}-{YYYYMMDD}.md`

Rules:
- Lowercase, hyphens only (no underscores, spaces, or special chars)
- Max 80 characters
- Descriptive enough to identify at a glance

Examples:
- `api-timeout-my-api-20260214.md`
- `missing-env-var-web-app-20260214.md`

### Step 6: Validate YAML

Read `references/yaml-schema.md` to validate all enum fields:
- `problem_type` must map to a known category directory
- `component` should be from the component enum when possible; project-specific values are acceptable
- `root_cause` must be from the root_cause enum (if provided)
- `resolution_type` must be from the resolution_type enum (if provided)
- `severity` must be: critical, high, medium, or low
- `symptoms` required **unless** `problem_type: principles`
- When `problem_type: principles`, `statement` and `confidence` are required

**Block creation if validation fails.** Report which fields are invalid and suggest corrections.

### Step 7: Create Solution or Principle File

1. Determine category directory from `problem_type` (e.g., `security` → `{solutions_path}/security/`, `principles` → `{solutions_path}/principles/`)
2. Read the appropriate template:
   - **Solutions**: `references/solution-template.md`
   - **Principles**: `references/principle-template.md`
3. Write the file with validated YAML frontmatter and structured content

### Step 8: Cross-Reference with Bidirectional Links

Links must be **bidirectional** — if file A references file B, file B must reference file A.

1. Identify related files from Step 4 results
2. Add `related_solutions` entries to the **new file** pointing to related files
3. **Update each related file** to add a backlink to the new file
   - Read the related file's `related_solutions` list
   - If the new file's path is not already present, append it
   - Cap at **5 entries per file** — if a related file already has 5 entries, skip adding the backlink to it
4. Present a summary to the user:

```
Created: {solutions_path}/{category}/{filename}.md
  Title: {title}
  Project: {project}
  Component: {component}
  Severity: {severity}

Related solutions:
  - [title](path) — {why related}

Updated backlinks in:
  - {path1} (now links back to new file)
  - {path2} (now links back to new file)
```

**Path format**: All `related_solutions` entries must use `category/filename.md` format (e.g., `debugging/my-fix-project-20260226.md`). Never use absolute paths, `~/` prefixes, or `knowledge/solutions/` prefixes.

### Step 9: Update Registry

Update the cross-project registry so this knowledge base is discoverable from other projects.

1. Read `~/.claude/compound-knowledge-registry.md` (if it doesn't exist, create it with the header from `references/registry-format.md`)
2. Determine the project name from the current working directory (lowercase, hyphens)
3. Check if an entry already exists for `{solutions_path}` (path is the unique key)
4. Count solution files: `Glob(pattern="**/*.md", path="{solutions_path}")` minus `critical-patterns.md`
5. Extract unique components: `Grep(pattern="^component:", path="{solutions_path}", output_mode="content")` — deduplicate and take top 10
6. **If entry exists**: Update `last_updated`, `solution_count`, and `primary_components` in-place
7. **If new entry**: Append a new entry block at the end of the file

---

## Directory Structure

```
{solutions_path}/
├── debugging/        # Service failures, error diagnosis
├── infrastructure/   # Networking, storage, resource issues
├── patterns/         # Design patterns, architectural approaches
├── workflow/         # Process improvements, scope management
├── performance/      # Speed, resource optimization
├── security/         # Vulnerability fixes, secrets management
├── ci-cd/           # Pipeline issues, publishing, deployment
├── configuration/    # Config management, env vars, settings
├── migration/        # System transitions, format changes
├── integration/      # Cross-system compatibility
├── principles/       # Engineering wisdom and governing principles
└── critical-patterns.md  # High-severity patterns (always read)
```

## References

- `references/yaml-schema.md` — YAML frontmatter field definitions and enum values
- `references/solution-template.md` — Template for new solution files
- `references/principle-template.md` — Template for new principle files
- `references/registry-format.md` — Cross-project registry schema and update rules
