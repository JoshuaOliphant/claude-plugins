---
name: verification-stack
description: >
  Use when running verification pipelines, checking test/lint/type status, or ensuring code quality
  gates pass before completing work. Trigger phrases include "run all checks", "make sure everything
  passes", "run the tests and linter", "verify the code", "check quality gates", "run ruff and pytest",
  "before I merge, check everything", "is the build green", "run the full verification pipeline", or
  any request to confirm code quality through automated tests, linting, formatting, and type checking
  before a commit, merge, or PR.
version: 1.0.0
---

# Verification Stack

## Goal

Run automated quality gates (format, lint, type check, test) as deterministic verification instead of manual approval. Verification replaces permission prompts — if checks pass, proceed; if they fail, fix and retry.

**Core Principle — Asymmetry of Verification**: Many tasks are easier to verify than to solve. Software development is highly verifiable through tests, linters, type checkers, and build systems.

## Dependencies

### Tools

- **Bash** — Runs all verification commands

### Connectors (language-specific)

| Language | Format | Lint | Types | Test |
|---|---|---|---|---|
| Python | `ruff format` | `ruff check` | `mypy` | `pytest` |
| TypeScript | `pnpm format` | `pnpm lint` | `tsc` | `vitest` |
| Go | `go fmt` | `golangci-lint` | `go build` | `go test` |

## Context

### Pipeline Order (Fast-Fail)

Run checks in this order — stop at first failure:

1. **Format** (auto-fix) — `uv run ruff format .`
2. **Lint** (auto-fix where possible) — `uv run ruff check . --fix`
3. **Type check** — `uv run mypy src/`
4. **Tests** (fast subset) — `uv run pytest tests/ -x --tb=short`
5. **Full test suite** — `uv run pytest tests/ --cov=src/`
6. **Security** (optional) — `uv run bandit -r src/ --severity-level high`

### Common Failure Patterns

| Failure | Fix |
|---|---|
| Lint: unused import | Remove the import |
| Type: missing return | Add return type annotation |
| Test: assertion failed | Fix logic or update test |
| Format: style violation | Auto-fix handles this |

## Process

### Step 1: Run the Pipeline

For Python projects:

```bash
uv run ruff format . && uv run ruff check . --fix && uv run mypy src/ && uv run pytest tests/ -x --tb=short
```

### Step 2: Handle Failures

1. **Read the error output** — Don't guess, analyze the actual failure
2. **Fix the specific issue** — Make targeted changes
3. **Re-run verification** — Confirm the fix works
4. **Continue** — Move to next task only when green

### Step 3: Continuous Verification

In autonomous workflows:
- **Before starting** — Check baseline is green
- **After each change** — Run relevant subset
- **Before closing a Bead** — Run full suite
- **Before merge** — Run full suite + integration tests

```bash
# Quick check during development
uv run pytest tests/test_specific.py -x

# Full verification before closing Bead
uv run ruff format . && uv run ruff check . --fix && uv run mypy src/ && uv run pytest tests/
```

## Output

A green or red verification result. Green means proceed. Red means fix and retry. No human approval needed — the pipeline is the gate.

### One-Command Script

For projects that want a single entry point:

```bash
#!/bin/bash
# scripts/verify.sh
set -e
echo "=== Formatting ===" && uv run ruff format .
echo "=== Linting ===" && uv run ruff check . --fix
echo "=== Type Checking ===" && uv run mypy src/
echo "=== Tests ===" && uv run pytest tests/ -x --tb=short
echo "=== All checks passed ==="
```
