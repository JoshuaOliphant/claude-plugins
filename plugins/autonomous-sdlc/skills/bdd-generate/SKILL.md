---
name: bdd-generate
description: This skill should be used when generating feature files, scaffolding BDD tests, creating step definitions, wiring pytest-bdd, converting acceptance criteria to Gherkin, or when acceptance criteria exist and need runnable test scaffolding. Trigger phrases include "generate feature files", "scaffold BDD tests", "create step definitions", "pytest-bdd", "Gherkin", and "make these acceptance criteria runnable".
version: 1.0.0
---

# BDD Test Scaffolder

Mechanical counterpart to `bdd-spec`. Takes structured acceptance criteria and produces runnable pytest-bdd scaffolding. This skill generates files — it is not conversational.

Input: acceptance criteria in Given/When/Then format (from `bdd-spec` output, a plan document, or directly from the human).

Output: `.feature` files, step definition stubs, pytest configuration, and directory structure.

## Prerequisite Check

Before generating any files, verify acceptance criteria exist. Check in this order:

1. Look for `bdd-spec` output in the current conversation (structured AC blocks with Given/When/Then)
2. Look for a plan document at `specs/{feature-slug}-plan.md` and extract the `## Acceptance Criteria` section
3. Check if the human provided AC directly in the current prompt

If no acceptance criteria are found:
- STOP generation
- Report: "No acceptance criteria found. To generate BDD tests, provide acceptance criteria in Given/When/Then format."
- Suggest: "Run `bdd-spec` to co-author acceptance criteria first, or provide them directly."

Do not generate generic or placeholder feature files. Every scenario must trace back to a specific acceptance criterion.

## Target Directory Structure

```
tests/bdd/
├── conftest.py                    # Shared BDD fixtures
├── features/
│   └── {feature}.feature          # Gherkin feature files
└── steps/
    ├── conftest.py                # Shared step definitions (cross-feature)
    └── test_{feature}.py          # Feature-specific step definitions
```

Create `tests/bdd/` alongside existing test directories. Do not move or restructure existing tests.

## pyproject.toml Configuration

Ensure pytest-bdd is installed and configured:

```bash
uv add --dev pytest-bdd
```

Add to `pyproject.toml` under `[tool.pytest.ini_options]` if not present:

```toml
[tool.pytest.ini_options]
markers = [
    "bdd: BDD acceptance tests",
]

[tool.pytest-bdd]
bdd_features_base_dir = "tests/bdd/features/"
```

Run BDD tests:

```bash
# BDD tests only
uv run pytest tests/bdd/ -x -m bdd

# All tests including BDD
uv run pytest tests/ -x
```

## Generation Workflow

Follow these steps in order:

### 1. Locate acceptance criteria

Run the prerequisite check. Extract each AC-N block, noting:
- The feature name (from the `## Acceptance Criteria: {Feature Name}` heading)
- Each AC number and title
- Given/When/Then content
- Edge cases and Scenario Outline tables

### 2. Ensure dependencies

```bash
uv add --dev pytest-bdd
```

Check `pyproject.toml` for existing pytest-bdd configuration. Add if missing.

### 3. Create directory structure

```bash
mkdir -p tests/bdd/features tests/bdd/steps
```

Create `tests/bdd/__init__.py`, `tests/bdd/features/__init__.py`, and `tests/bdd/steps/__init__.py` if they don't exist (empty files).

### 4. Configure pytest

Add BDD marker and features base directory to `pyproject.toml` if not already present. See the pyproject.toml Configuration section.

### 5. Generate .feature files

Create one `.feature` file per feature. Map acceptance criteria to Gherkin:

- AC heading → Feature name
- AC-N blocks → individual Scenarios
- Bold **Given/When/Then** → Gherkin `Given`/`When`/`Then` keywords
- `and` continuations → Gherkin `And` keyword
- Edge case tables → `Scenario Outline` with `Examples`
- Shared preconditions across all ACs → `Background`

### 6. Generate step definition stubs

Create one test file per feature in `tests/bdd/steps/`. Use the `scenarios()` shortcut to auto-bind all scenarios from the feature file. Generate `@given`, `@when`, `@then` stubs with `parsers.parse()` for parameterized steps and `TODO` markers for implementation.

### 7. Verify scaffolding

Run collection check then execution:

```bash
# Verify all scenarios are discovered
uv run pytest tests/bdd/ --collect-only

# Run BDD tests (stubs will fail at TODO markers)
uv run pytest tests/bdd/ -x
```

Collection should succeed with zero errors. Execution will show failures at TODO stubs — this is expected and correct. The stubs are ready for implementation.

## File Templates

### Feature File

```gherkin
# ABOUTME: BDD feature file for {feature_name}
# ABOUTME: Generated from acceptance criteria — scenarios map to AC-N numbers

Feature: {Feature Name}
    {One-line feature description}

    Background:
        Given {shared precondition across all scenarios}

    @ac-1
    Scenario: {AC-1 title}
        Given {precondition}
        When {action}
        Then {outcome}
        And {additional outcome}

    @ac-2
    Scenario: {AC-2 title}
        Given {precondition}
        When {action}
        Then {outcome}

    @ac-3
    Scenario Outline: {AC-3 title — parameterized}
        Given {precondition}
        When the user submits <input>
        Then the system displays <error_message>

        Examples:
            | input          | error_message        |
            | empty email    | Email is required    |
            | not-an-email   | Invalid email format |
```

Notes:
- Tag each scenario with `@ac-N` to maintain traceability to acceptance criteria
- Use `Background` only when a precondition applies to *every* scenario in the feature
- Keep step text close to natural language — avoid implementation jargon

### Step Definitions

```python
# ABOUTME: Step definitions for {feature_name} BDD tests
# ABOUTME: Stubs generated from acceptance criteria — implement TODO markers

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Auto-bind all scenarios from the feature file
scenarios("../features/{feature}.feature")


@given(parsers.parse("a registered user with email {email}"), target_fixture="user")
def given_registered_user(email):
    """Set up a registered user."""
    # TODO: Implement — create or retrieve a user with the given email
    raise NotImplementedError("Implement this step")


@when(parsers.parse("the user submits the login form with {credentials}"))
def when_user_submits_login(credentials, user):
    """Perform the login action."""
    # TODO: Implement — submit login form with the given credentials
    raise NotImplementedError("Implement this step")


@then(parsers.parse("the user is redirected to {destination}"))
def then_user_redirected(destination):
    """Verify redirect destination."""
    # TODO: Implement — assert the user was redirected to the expected destination
    raise NotImplementedError("Implement this step")


@then(parsers.parse("the system displays {message}"))
def then_system_displays(message):
    """Verify displayed message."""
    # TODO: Implement — assert the expected message is shown to the user
    raise NotImplementedError("Implement this step")
```

Notes:
- `scenarios()` auto-discovers and binds all scenarios from the feature file — no need for individual `@scenario` decorators
- Use `parsers.parse()` for steps with parameters (curly braces)
- Use `target_fixture` to inject state from `@given` steps into `@when` and `@then` steps
- Raise `NotImplementedError` in stubs so failures are explicit, not silent

### Shared Fixtures (tests/bdd/conftest.py)

```python
# ABOUTME: Shared BDD fixtures for acceptance tests
# ABOUTME: Common setup used across multiple feature files

import pytest


@pytest.fixture
def app_client():
    """Provide a test client for the application."""
    # TODO: Implement — return a test client instance
    raise NotImplementedError("Implement shared fixture")
```

### Shared Steps (tests/bdd/steps/conftest.py)

```python
# ABOUTME: Shared step definitions used across multiple BDD features
# ABOUTME: Steps that appear in more than one feature file belong here

from pytest_bdd import given, parsers


@given(parsers.parse("the application is running"), target_fixture="app")
def given_app_running():
    """Ensure the application is available for testing."""
    # TODO: Implement — start or connect to the application
    raise NotImplementedError("Implement shared step")
```

## Integration with Existing Skills

BDD and TDD serve complementary roles in the testing pyramid:

- **BDD (this skill)** — Outer loop. Acceptance-level tests that verify the system behaves correctly from the user's perspective. Feature files describe *what* the system does.
- **TDD (`tdd-workflow`)** — Inner loop. Unit-level tests that verify individual components work correctly. Test files describe *how* the code works.

BDD tests run through the existing verification pipeline without modification. The `verification-stack` skill's `uv run pytest tests/ -x` command auto-discovers BDD tests in `tests/bdd/` via standard pytest collection. No changes to `verification-stack` are needed.

Workflow in practice:
1. `bdd-spec` produces acceptance criteria (human-readable)
2. `bdd-generate` scaffolds feature files and step stubs (machine-runnable)
3. Builder implements step definitions using TDD (inner loop red-green-refactor)
4. Validator confirms all BDD scenarios pass (outer loop verification)

For data table support beyond Scenario Outlines, consider `pytest-bdd-ng` which extends Gherkin with richer table types.

## Resources

- **`references/pytest_bdd_reference.md`** — Consult for detailed pytest-bdd syntax, parser types, step decorator patterns, conftest discovery rules, and tag-to-marker mapping. Use when generating step definitions or troubleshooting pytest-bdd configuration.
