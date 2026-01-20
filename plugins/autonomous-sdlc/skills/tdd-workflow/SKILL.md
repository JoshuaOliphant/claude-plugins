---
name: tdd-workflow
description: Use when implementing features with test-driven development, writing tests before code, or following the red-green-refactor cycle
version: 1.0.0
---

# Test-Driven Development Workflow

TDD is the foundation of verification-driven development. Write tests first, then implement code to make them pass.

## The Red-Green-Refactor Cycle

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   RED: Write failing test                           │
│         ↓                                           │
│   GREEN: Write minimal code to pass                 │
│         ↓                                           │
│   REFACTOR: Improve code while keeping tests green  │
│         ↓                                           │
│   (repeat)                                          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Step-by-Step Process

### 1. RED - Write a Failing Test

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

Run test to confirm it fails:
```bash
uv run pytest tests/test_user_service.py::test_create_user_returns_user_with_id -x
# Expected: FAILED (UserService doesn't exist)
```

### 2. GREEN - Minimal Implementation

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

Run test to confirm it passes:
```bash
uv run pytest tests/test_user_service.py::test_create_user_returns_user_with_id -x
# Expected: PASSED
```

### 3. REFACTOR - Improve While Green

Now improve the code (add validation, better types, etc.) while keeping tests green:

```python
# src/user_service.py
from dataclasses import dataclass, field
from typing import Optional
import uuid

@dataclass
class User:
    name: str
    email: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

class UserService:
    def create_user(self, name: str, email: str) -> User:
        if not name.strip():
            raise ValueError("Name cannot be empty")
        if "@" not in email:
            raise ValueError("Invalid email format")
        return User(name=name.strip(), email=email.lower())
```

Run full test suite:
```bash
uv run pytest tests/test_user_service.py -x
# Should still pass
```

### 4. Add More Tests

Continue the cycle with edge cases:

```python
def test_create_user_validates_empty_name():
    service = UserService()

    with pytest.raises(ValueError, match="Name cannot be empty"):
        service.create_user(name="", email="test@example.com")

def test_create_user_validates_email_format():
    service = UserService()

    with pytest.raises(ValueError, match="Invalid email"):
        service.create_user(name="Alice", email="not-an-email")

def test_create_user_normalizes_email():
    service = UserService()

    user = service.create_user(name="Alice", email="Alice@Example.COM")

    assert user.email == "alice@example.com"
```

## TDD Rules

1. **Never write production code without a failing test**
2. **Write only enough test to fail** (compilation failures count)
3. **Write only enough code to pass the failing test**
4. **Refactor only when tests are green**

## Test Organization

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── test_user_service.py
│   └── test_auth.py
├── integration/             # Tests with real dependencies
│   ├── test_user_api.py
│   └── test_database.py
└── e2e/                     # Full system tests
    └── test_user_workflow.py
```

## Pytest Markers for Speed

```python
# conftest.py
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks integration tests")
```

```python
# tests/test_slow.py
@pytest.mark.slow
def test_large_data_processing():
    ...

@pytest.mark.integration
def test_database_connection():
    ...
```

Run fast tests only:
```bash
uv run pytest -m "not slow and not integration" -x
```

## Coverage Guidance

Aim for meaningful coverage, not 100%:

```bash
uv run pytest --cov=src/ --cov-report=term-missing
```

Focus on:
- Critical business logic: 90%+
- Edge cases and error paths
- Integration points

Don't obsess over:
- Simple getters/setters
- Framework boilerplate
- Generated code

## Test-First Checklist

Before implementing any feature:

- [ ] Write test for happy path
- [ ] Write test for error cases
- [ ] Write test for edge cases
- [ ] Run tests (confirm RED)
- [ ] Implement minimal code
- [ ] Run tests (confirm GREEN)
- [ ] Refactor if needed
- [ ] Run full suite
