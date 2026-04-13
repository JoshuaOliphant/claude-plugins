---
name: bdd-generate
description: >
  Use AFTER bdd-spec has produced acceptance criteria, or when the user has existing Given/When/Then
  scenarios that need pytest-bdd scaffolding. MUST NOT run without existing acceptance criteria —
  invoke bdd-spec first if none exist. Trigger: "generate feature files", "scaffold BDD tests",
  "wire up pytest-bdd", "make these criteria runnable", "create step definitions". This is
  mechanical code generation, not spec writing.
version: 1.0.0
context: fork
effort: medium
allowed-tools:
  - Bash
  - Write
  - Read
---

# BDD Test Scaffolder

## Goal

Take structured acceptance criteria (Given/When/Then) and produce runnable pytest-bdd scaffolding: `.feature` files, step definition stubs, pytest configuration, and directory structure. This skill generates files — it is not conversational.

## Dependencies

### Tools

- **Bash** — Runs `uv add`, `mkdir`, `pytest --collect-only`
- **Write** — Creates feature files, step definitions, conftest.py

### Connectors

- **pytest-bdd** — Installed via `uv add --dev pytest-bdd`
- **Acceptance criteria** — Input from `bdd-spec` output, a plan document, or directly from the user

## Context

### Prerequisite Guard

Before generating any files, verify acceptance criteria exist. Check in this order:

1. `bdd-spec` output in the current conversation (structured AC blocks)
2. Plan document at `specs/{feature-slug}-plan.md` → extract `## Acceptance Criteria`
3. AC provided directly in the current prompt

> **STOP if no acceptance criteria are found.** Do not generate generic or placeholder feature files. Report: "No acceptance criteria found." Suggest: "Run `bdd-spec` to co-author acceptance criteria first."

Every scenario must trace back to a specific acceptance criterion.

### Target Directory Structure

```
tests/bdd/
├── conftest.py                    # Shared BDD fixtures
├── features/
│   └── {feature}.feature          # Gherkin feature files
└── steps/
    ├── conftest.py                # Shared step definitions (cross-feature)
    └── test_{feature}.py          # Feature-specific step definitions
```

### AC → Gherkin Mapping

| Acceptance Criteria | Gherkin |
|---|---|
| AC heading | Feature name |
| AC-N blocks | Individual Scenarios |
| Bold **Given/When/Then** | Gherkin `Given`/`When`/`Then` keywords |
| `and` continuations | Gherkin `And` keyword |
| Edge case tables | `Scenario Outline` with `Examples` |
| Shared preconditions across all ACs | `Background` |

Tag each scenario with `@ac-N` for traceability.

### Integration with Other Skills

- **BDD** (this skill) — Outer loop. Acceptance-level tests verifying user-perspective behavior.
- **TDD** (`tdd-workflow`) — Inner loop. Unit-level tests verifying component internals.
- **Verification** (`verification-stack`) — `uv run pytest tests/ -x` auto-discovers BDD tests. No config changes needed.

For detailed pytest-bdd syntax, parser types, and step decorator patterns:

→ **`references/pytest_bdd_reference.md`**

## Process

### Step 0: Load Stored Feedback

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc show-feedback
```

Apply relevant feedback: **test_generation**, **bdd_workflow**, **general**.

### Step 1: Locate Acceptance Criteria

Run the prerequisite guard. Extract each AC-N block, noting feature name, AC numbers, Given/When/Then content, edge cases, and Scenario Outline tables.

### Step 2: Ensure Dependencies

```bash
uv add --dev pytest-bdd
```

Add to `pyproject.toml` if not present:

```toml
[tool.pytest.ini_options]
markers = ["bdd: BDD acceptance tests"]

[tool.pytest-bdd]
bdd_features_base_dir = "tests/bdd/features/"
```

### Step 3: Create Directory Structure

```bash
mkdir -p tests/bdd/features tests/bdd/steps
```

Create `__init__.py` files in each directory if they don't exist.

### Step 4: Generate .feature Files

One `.feature` file per feature:

```gherkin
# ABOUTME: BDD feature file for {feature_name}
# ABOUTME: Generated from acceptance criteria — scenarios map to AC-N numbers

Feature: {Feature Name}
    {One-line description}

    Background:
        Given {shared precondition}

    @ac-1
    Scenario: {AC-1 title}
        Given {precondition}
        When {action}
        Then {outcome}
        And {additional outcome}

    @ac-2
    Scenario Outline: {AC-2 title — parameterized}
        Given {precondition}
        When the user submits <input>
        Then the system displays <error_message>

        Examples:
            | input        | error_message        |
            | empty email  | Email is required    |
```

### Step 5: Generate Step Definition Stubs

One test file per feature in `tests/bdd/steps/`:

```python
# ABOUTME: Step definitions for {feature_name} BDD tests
# ABOUTME: Stubs generated from acceptance criteria — implement TODO markers

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

scenarios("../features/{feature}.feature")


@given(parsers.parse("a registered user with email {email}"), target_fixture="user")
def given_registered_user(email):
    """Set up a registered user."""
    # TODO: Implement
    raise NotImplementedError("Implement this step")


@when(parsers.parse("the user submits the login form with {credentials}"))
def when_user_submits_login(credentials, user):
    """Perform the login action."""
    # TODO: Implement
    raise NotImplementedError("Implement this step")


@then(parsers.parse("the system displays {message}"))
def then_system_displays(message):
    """Verify displayed message."""
    # TODO: Implement
    raise NotImplementedError("Implement this step")
```

Notes:
- `scenarios()` auto-discovers all scenarios from the feature file
- Use `parsers.parse()` for parameterized steps
- Use `target_fixture` to inject state from `@given` into `@when`/`@then`
- `NotImplementedError` makes failures explicit, not silent

### Step 6: Generate Shared Fixtures

Create `tests/bdd/conftest.py` and `tests/bdd/steps/conftest.py` with common fixtures and shared steps.

### Step 7: Verify Scaffolding

```bash
# Verify all scenarios are discovered
uv run pytest tests/bdd/ --collect-only

# Run BDD tests (stubs will fail at TODO markers — expected)
uv run pytest tests/bdd/ -x
```

Collection should succeed with zero errors. Execution failures at TODO stubs are expected and correct.

## Output

| File | Purpose |
|---|---|
| `tests/bdd/features/{feature}.feature` | Gherkin scenarios tagged with `@ac-N` |
| `tests/bdd/steps/test_{feature}.py` | Step definition stubs with `NotImplementedError` |
| `tests/bdd/conftest.py` | Shared BDD fixtures |
| `tests/bdd/steps/conftest.py` | Shared step definitions (cross-feature) |

Stubs are ready for implementation via TDD inner loop (red-green-refactor on each step).
