---
name: tdd-workflow
description: >
  Use when implementing features with test-driven development, writing tests before implementation
  code, or following the red-green-refactor cycle. Trigger phrases include "write a failing test first",
  "implement this with TDD", "test first then code", "red green refactor", "let's do TDD", "write the
  test before the implementation", or when the user asks to build a feature and the project practices
  TDD. This skill enforces the discipline of writing a failing test, making it pass with minimal code,
  then refactoring — never skipping the test-first step.
version: 1.0.0
---

# Test-Driven Development Workflow

## Goal

Enforce the discipline of writing tests before implementation code. Every feature starts with a failing test (RED), passes with minimal code (GREEN), then improves through refactoring while green. Never skip the test-first step.

## Dependencies

### Tools

- **pytest** — Test runner. Invoked via `uv run pytest`.
- **Bash** — Runs test commands to confirm RED/GREEN status.

### Connectors

- **Project test infrastructure** — Existing `tests/` directory with pytest configuration.

## Context

### The Red-Green-Refactor Cycle

```
RED: Write failing test
  ↓
GREEN: Write minimal code to pass
  ↓
REFACTOR: Improve code while keeping tests green
  ↓
(repeat)
```

### TDD Rules

1. **Never write production code without a failing test**
2. **Write only enough test to fail** (compilation failures count)
3. **Write only enough code to pass the failing test**
4. **Refactor only when tests are green**

### Test Organization

```
tests/
├── unit/                    # Fast, isolated tests
├── integration/             # Tests with real dependencies
└── e2e/                     # Full system tests
```

### Coverage Guidance

Focus on meaningful coverage, not 100%:
- Critical business logic: 90%+
- Edge cases and error paths
- Integration points

Don't obsess over: simple getters/setters, framework boilerplate, generated code.

## Process

### Step 0: Load Stored Feedback

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/feedback_manager.py autonomous-sdlc show-feedback
```

Apply relevant feedback: **tdd_workflow**, **test_generation**, **general**.

### Step 1: RED — Write a Failing Test

```python
# tests/test_user_service.py
def test_create_user_returns_user_with_id():
    """Test that creating a user returns a user with an assigned ID."""
    service = UserService()
    user = service.create_user(name="Alice", email="alice@example.com")

    assert user.id is not None
    assert user.name == "Alice"
    assert user.email == "alice@example.com"
```

Run to confirm failure:
```bash
uv run pytest tests/test_user_service.py::test_create_user_returns_user_with_id -x
# Expected: FAILED (UserService doesn't exist)
```

### Step 2: GREEN — Minimal Implementation

Write just enough code to make the test pass:

```python
# src/user_service.py
from dataclasses import dataclass
import uuid

@dataclass
class User:
    id: str
    name: str
    email: str

class UserService:
    def create_user(self, name: str, email: str) -> User:
        return User(id=str(uuid.uuid4()), name=name, email=email)
```

Run to confirm pass:
```bash
uv run pytest tests/test_user_service.py::test_create_user_returns_user_with_id -x
# Expected: PASSED
```

### Step 3: REFACTOR — Improve Structure While Green

Refactoring means improving code *structure* without changing behavior. Do not add new features here.

```python
# src/user_service.py — structural improvement only
from dataclasses import dataclass, field
import uuid

@dataclass
class User:
    name: str
    email: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

class UserService:
    def create_user(self, name: str, email: str) -> User:
        return User(name=name, email=email)
```

```bash
uv run pytest tests/test_user_service.py -x
# Should still pass — behavior unchanged, structure improved
```

### Step 4: Next RED Cycle — Add Validation

New behavior requires a new failing test first:

```python
# RED: Write failing test for validation
def test_create_user_validates_empty_name():
    service = UserService()
    with pytest.raises(ValueError, match="Name cannot be empty"):
        service.create_user(name="", email="test@example.com")
```

```bash
uv run pytest tests/test_user_service.py -x
# Expected: FAILED (no validation exists yet)
```

```python
# GREEN: Add just enough code to pass
class UserService:
    def create_user(self, name: str, email: str) -> User:
        if not name.strip():
            raise ValueError("Name cannot be empty")
        return User(name=name, email=email)
```

Then repeat for email validation, normalization, etc. — always RED first.

### Test-First Checklist

Before implementing any feature:

- [ ] Write test for happy path
- [ ] Write test for error cases
- [ ] Write test for edge cases
- [ ] Run tests (confirm RED)
- [ ] Implement minimal code
- [ ] Run tests (confirm GREEN)
- [ ] Refactor if needed
- [ ] Run full suite

## Output

Working tests and implementation code produced through the red-green-refactor cycle. The test suite serves as living documentation of the system's behavior.
