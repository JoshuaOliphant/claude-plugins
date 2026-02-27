---
name: compound-knowledge
description: >
  CAPTURE MODE: Use after solving a non-trivial problem, discovering a reusable
  pattern, validating a principle through experience, completing non-trivial
  debugging, making architecture decisions worth preserving, or generating any
  reusable insight. Triggers on "that worked", "it's fixed", "problem solved",
  "capture that", or explicit /compound-knowledge invocation.
  RETRIEVAL MODE: Use when starting debugging, planning a feature, encountering
  an error, working in an unfamiliar codebase, making design decisions, or any
  time past experience might help. Triggers on "have we seen this before",
  "search for solutions", "check knowledge", or when beginning any non-trivial
  investigation.
  Captures solved problems AND engineering principles as structured
  YAML-frontmatter files for grep-based retrieval.
allowed-tools: [Read, Write, Edit, Grep, Glob]
---

# Compound Knowledge

Capture solved problems as searchable solution files. Surface past solutions when facing similar problems.

## Path Resolution

Before any capture or retrieval operation, resolve the solutions directory path.

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

## Registry

A central registry at `~/.claude/compound-knowledge-registry.md` tracks all knowledge bases on the machine. This enables cross-project solution search — a Docker fix captured in project A is discoverable when debugging the same issue in project B.

See `references/registry-format.md` for the full schema and update rules.

**When registration happens:**
1. **`/compound-knowledge:setup`** — registers after creating the directory structure
2. **After capture** — updates entry (last_updated, solution_count, primary_components) as final step
3. **First retrieval from a path** — registers if not already present (idempotent)

If the resolved directory does not exist, inform the user:
> "Solutions directory not found at `{solutions_path}`. Run `/compound-knowledge:setup` to initialize it."

---

## When This Skill Activates

### Capture Mode (Writing Solutions or Principles)
- User says "that worked", "it's fixed", "problem solved", or similar confirmation
- User explicitly invokes `/compound-knowledge`
- A non-trivial debugging session concludes successfully
- A reusable pattern or principle is discovered or validated
- An architecture decision is made that future sessions should know about
- A non-obvious insight is generated that applies beyond the current task

### Retrieval Mode (Finding Solutions and Principles)
- Starting a non-trivial debugging session
- Planning a feature that touches previously-solved domains
- Encountering errors that might have documented solutions
- Working in an unfamiliar codebase or domain
- Making design decisions where past experience would help
- Any time past engineering wisdom might prevent repeated mistakes

## Triviality Filter

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

When capturing knowledge, determine whether you're recording a **solution** (specific problem fix) or a **principle** (generalizable engineering wisdom).

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

Look for trigger phrases in conversation:
- "That worked" / "It's fixed" / "Problem solved"
- "Finally got it working"
- Explicit `/compound-knowledge` invocation
- Test suite going from red to green after debugging

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
- `docker-build-cache-cli-tool-20260214.md`

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

### Step 8: Cross-Reference and Confirm

1. Add `related_solutions` links if similar files were found in Step 4
2. Present a summary to the user:

```
Created: {solutions_path}/{category}/{filename}.md
  Title: {title}
  Project: {project}
  Component: {component}
  Severity: {severity}

Related solutions:
  - [title](path) — {why related}
```

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

## Retrieval Workflow (Delegation)

When starting work that could benefit from past solutions:

### Step 1: Resolve Solutions Path

Follow the Path Resolution algorithm above. Store the result as `{solutions_path}`.

### Step 2: Delegate to Knowledge Researcher

```
Task(
  subagent_type="compound-knowledge:knowledge-researcher",
  model="haiku",
  prompt="Search for solutions related to: {task_description}. Project: {project_name}. Keywords: {extracted_keywords}. Solutions path: {solutions_path}. Registry path: ~/.claude/compound-knowledge-registry.md",
  description="Search past solutions"
)
```

The researcher reads the registry to identify other knowledge bases for cross-project search when primary results are thin (<3 hits).

### When to Invoke Retrieval

- **Before non-trivial debugging**: "Let me check if we've seen this before..."
- **During planning phases**: "Checking for relevant past solutions..."
- **When encountering errors**: Search by symptom/error message
- **When working on a project**: Search by project name for all related solutions

### Interpreting Results

The knowledge-researcher returns:
1. **Critical patterns** — always-relevant warnings from `critical-patterns.md`
2. **Ranked solutions** — scored by project, component, symptom, and tag relevance
3. **Recommendations** — actionable suggestions based on found solutions

Surface the top results to the user and incorporate insights into your approach.

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
