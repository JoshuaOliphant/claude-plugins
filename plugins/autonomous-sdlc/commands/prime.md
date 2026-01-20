---
name: prime
description: Quickly understand a codebase before starting work - reads structure, key docs, and summarizes understanding
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
---

# Prime

Quickly understand the codebase before starting work. This is the orientation step that helps you understand the project's structure, patterns, and conventions.

## Process

### 1. Discover Structure

```bash
# See all tracked files
git ls-files

# Check project type
ls -la
```

### 2. Read Key Documentation

Read these files in order (skip if they don't exist):

1. **README.md** - Project overview, setup instructions
2. **CLAUDE.md** - AI-specific instructions and patterns
3. **pyproject.toml** or **package.json** - Dependencies and scripts
4. **docs/ARCHITECTURE.md** or similar - Architecture overview

### 3. Identify Key Patterns

Look for:
- **Source code location**: `src/`, `app/`, `lib/`, root?
- **Test location**: `tests/`, `test/`, `__tests__/`?
- **Configuration**: `.env.sample`, config files
- **Build system**: Makefile, scripts/, package.json scripts

### 4. Summarize Understanding

Provide a summary in this format:

```
## Project Overview
[1-2 sentences about what this project does]

## Technology Stack
- Language: [Python/TypeScript/Go/etc.]
- Framework: [FastAPI/Next.js/etc.]
- Database: [if applicable]
- Package Manager: [uv/npm/etc.]

## Key Directories
- Source: [path]
- Tests: [path]
- Config: [path]

## Development Commands
- Run: [command]
- Test: [command]
- Lint: [command]

## Patterns Noted
- [Any notable patterns, conventions, or architecture decisions]

## Ready to Work
[Confirm understanding and readiness to proceed]
```

## Tips

- If CLAUDE.md exists, it contains project-specific instructions - prioritize reading it
- Look for `.claude/` directory with additional context
- Check for Beads integration (`bd ready` to see available tasks)
- Note any custom tooling or scripts in `scripts/` or `tools/`
