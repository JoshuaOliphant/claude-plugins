---
name: verification-stack
description: Use when running verification pipelines, checking test/lint/type status, or ensuring code quality gates pass before completing work
version: 1.0.0
---

# Verification Stack

Verification-driven development uses automated checks as gates instead of manual approval. This skill teaches the verification pipeline that enables autonomous development.

## Core Principle

**Asymmetry of Verification**: Many tasks are easier to verify than to solve. Software development is highly verifiable through:

- Tests (unit, integration, e2e)
- Linters and formatters
- Type checkers
- Build systems
- Security scanners

## The Verification Pipeline

Run checks in this order (fast-fail):

```bash
# 1. Format (auto-fix)
uv run ruff format .

# 2. Lint (auto-fix where possible)
uv run ruff check . --fix

# 3. Type check
uv run mypy src/

# 4. Tests (fast subset first)
uv run pytest tests/ -x --tb=short

# 5. Full test suite
uv run pytest tests/ --cov=src/

# 6. Security (optional)
uv run bandit -r src/ --severity-level high
```

## One-Command Verification

Create a verification script for the project:

```bash
#!/bin/bash
# scripts/verify.sh
set -e

echo "=== Formatting ==="
uv run ruff format .

echo "=== Linting ==="
uv run ruff check . --fix

echo "=== Type Checking ==="
uv run mypy src/

echo "=== Tests ==="
uv run pytest tests/ -x --tb=short

echo "=== All checks passed ==="
```

Run with: `bash scripts/verify.sh`

## Language-Specific Stacks

### Python (uv + ruff + mypy + pytest)

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy src/
uv run pytest tests/ -x
```

### TypeScript (pnpm + eslint + tsc + vitest)

```bash
pnpm format
pnpm lint --fix
pnpm typecheck
pnpm test
```

### Go

```bash
go fmt ./...
golangci-lint run --fix
go build ./...
go test ./...
```

## Verification as Gate

The key insight: **verification replaces permission prompts**.

Instead of:
```
Claude: "Can I proceed with implementing this feature?"
Human: "Yes"
```

Use:
```
Claude: [implements feature]
Claude: [runs verification]
Verification: PASS → proceed
Verification: FAIL → fix and retry
```

## Handling Failures

When verification fails:

1. **Read the error output** - Don't guess, analyze the actual failure
2. **Fix the specific issue** - Make targeted changes
3. **Re-run verification** - Confirm the fix works
4. **Continue** - Move to next task only when green

### Common Failure Patterns

| Failure | Fix |
|---------|-----|
| Lint: unused import | Remove the import |
| Type: missing return | Add return type annotation |
| Test: assertion failed | Fix logic or update test |
| Format: style violation | Auto-fix handles this |

## Pre-Commit Integration

Add verification as git hook:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

## Continuous Verification

In autonomous workflows:

1. **Before starting**: Check baseline is green
2. **After each change**: Run relevant subset
3. **Before closing Bead**: Run full suite
4. **Before merge**: Run full suite + integration tests

```bash
# Quick check during development
uv run pytest tests/test_specific.py -x

# Full verification before closing Bead
uv run ruff format . && uv run ruff check . --fix && uv run mypy src/ && uv run pytest tests/
```
