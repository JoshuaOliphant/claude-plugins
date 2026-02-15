---
name: compound-knowledge
description: >
  This skill should be used when the user says "that worked", "it's fixed",
  "problem solved", "capture that solution", or explicitly invokes /compound-knowledge
  after solving a non-trivial problem. Also activates when starting debugging or
  planning work where past solutions might help — triggered by phrases like
  "check if we've seen this before" or "search for solutions". Captures solved
  problems as structured YAML-frontmatter solution files for grep-based retrieval.
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

If the resolved directory does not exist, inform the user:
> "Solutions directory not found at `{solutions_path}`. Run `/compound-knowledge:setup` to initialize it."

---

## When This Skill Activates

### Capture Mode (Writing Solutions)
- User says "that worked", "it's fixed", "problem solved", or similar confirmation
- User explicitly invokes `/compound-knowledge`
- A non-trivial debugging session concludes successfully

### Retrieval Mode (Finding Solutions)
- Starting a non-trivial debugging session
- Planning a feature that touches previously-solved domains
- Encountering errors that might have documented solutions

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

---

## Capture Workflow (8 Steps)

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

Extract from the conversation:

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

**Block creation if validation fails.** Report which fields are invalid and suggest corrections.

### Step 7: Create Solution File

1. Determine category directory from `problem_type` (e.g., `security` → `{solutions_path}/security/`)
2. Read `references/solution-template.md` for the file structure
3. Write the solution file with validated YAML frontmatter and structured content

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
  prompt="Search for solutions related to: {task_description}. Project: {project_name}. Keywords: {extracted_keywords}. Solutions path: {solutions_path}",
  description="Search past solutions"
)
```

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
└── critical-patterns.md  # High-severity patterns (always read)
```

## References

- `references/yaml-schema.md` — YAML frontmatter field definitions and enum values
- `references/solution-template.md` — Template for new solution files
