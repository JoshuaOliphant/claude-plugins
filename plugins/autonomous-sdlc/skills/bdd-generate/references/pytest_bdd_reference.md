# pytest-bdd Quick Reference

Syntax reference for pytest-bdd — the pytest plugin for Behavior-Driven Development with Gherkin feature files.

## Gherkin Syntax

### Feature File Structure

```gherkin
@feature-tag
Feature: Feature Name
    Optional multi-line description
    of what this feature does.

    Background:
        Given a shared precondition
        And another shared precondition

    @scenario-tag
    Scenario: Descriptive scenario name
        Given a precondition
        When an action occurs
        Then an outcome is verified
        And another outcome is verified
        But a negative outcome is also checked

    @outline-tag
    Scenario Outline: Parameterized scenario
        Given a user with role <role>
        When the user attempts to <action>
        Then the result is <expected>

        Examples:
            | role    | action       | expected |
            | admin   | delete user  | success  |
            | member  | delete user  | denied   |
```

### Keywords

| Keyword | Purpose |
|---------|---------|
| `Feature` | Groups related scenarios |
| `Background` | Runs before each scenario in the feature |
| `Scenario` | A single test case |
| `Scenario Outline` | A parameterized template (runs once per Examples row) |
| `Examples` | Data table for Scenario Outline |
| `Given` | Precondition / setup |
| `When` | Action / trigger |
| `Then` | Expected outcome / assertion |
| `And` | Continues previous Given/When/Then |
| `But` | Negative continuation of previous step |
| `@tag` | Tags for filtering and markers |

## Step Definition Decorators

### Basic Steps

```python
from pytest_bdd import given, when, then

@given("a registered user")
def given_registered_user():
    return {"name": "Alice", "registered": True}

@when("the user logs in")
def when_user_logs_in():
    pass

@then("the dashboard is displayed")
def then_dashboard_displayed():
    assert True  # Replace with real assertion
```

### Steps with target_fixture

Use `target_fixture` to inject step return values into other steps as fixtures:

```python
@given("a registered user", target_fixture="user")
def given_registered_user():
    return User(name="Alice")

@when("the user logs in", target_fixture="response")
def when_user_logs_in(user):
    return login(user)

@then("the dashboard is displayed")
def then_dashboard_displayed(response):
    assert response.status_code == 200
```

## Parser Types

### parsers.parse() — Recommended Default

Uses Python format-string syntax with named placeholders:

```python
from pytest_bdd import parsers

@given(parsers.parse("a user named {name} with email {email}"), target_fixture="user")
def given_user(name, email):
    return User(name=name, email=email)
```

### parsers.re() — Regex Patterns

For complex matching with capture groups:

```python
@then(parsers.re(r"the response status is (?P<status>\d+)"))
def then_status(status):
    assert int(status) == expected_status
```

### parsers.string() — Exact String Match

No parameters, fastest matching:

```python
@given(parsers.string("the database is empty"))
def given_empty_db():
    db.clear()
```

### String Literal — Shorthand for parsers.string()

```python
@given("the database is empty")
def given_empty_db():
    db.clear()
```

## Scenario Binding

### scenarios() — Auto-Discover All Scenarios

```python
from pytest_bdd import scenarios

# Bind all scenarios from a feature file
scenarios("../features/login.feature")

# Bind from multiple files
scenarios("../features/login.feature", "../features/registration.feature")
```

### @scenario — Explicit Single Scenario

```python
from pytest_bdd import scenario

@scenario("../features/login.feature", "Successful login")
def test_successful_login():
    pass  # Steps handle the implementation
```

## Conftest Discovery

pytest-bdd discovers step definitions through pytest's conftest.py mechanism:

- `tests/bdd/conftest.py` — shared fixtures for all BDD tests
- `tests/bdd/steps/conftest.py` — shared step definitions used across features
- `tests/bdd/steps/test_{feature}.py` — feature-specific steps

Step definitions in conftest.py are available to all test files in the same directory and below. Place cross-feature steps (like "Given the application is running") in `steps/conftest.py`.

## Tag-to-Marker Mapping

Gherkin tags map directly to pytest markers:

```gherkin
@slow
@integration
Scenario: Database migration test
    ...
```

Run with marker filtering:

```bash
# Run only scenarios tagged @smoke
uv run pytest tests/bdd/ -m smoke

# Exclude slow scenarios
uv run pytest tests/bdd/ -m "not slow"

# Combine markers
uv run pytest tests/bdd/ -m "smoke and not slow"
```

Register custom markers in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "bdd: BDD acceptance tests",
    "smoke: Quick smoke tests",
    "slow: Long-running tests",
]
```

## Scenario Outline Patterns

### Basic Parameterization

```gherkin
Scenario Outline: Validate email format
    Given a registration form
    When the user enters email "<email>"
    Then the validation result is "<result>"

    Examples:
        | email              | result  |
        | user@example.com   | valid   |
        | not-an-email       | invalid |
        | @missing-local     | invalid |
```

Step definition for outline:

```python
@when(parsers.parse('the user enters email "{email}"'))
def when_enter_email(email):
    return validate_email(email)

@then(parsers.parse('the validation result is "{result}"'))
def then_validation_result(result):
    assert actual_result == result
```

### Multiple Examples Tables

```gherkin
Scenario Outline: Access control
    Given a user with role "<role>"
    When the user accesses "<resource>"
    Then the response is <status>

    Examples: Admin access
        | role  | resource     | status |
        | admin | /users       | 200    |
        | admin | /settings    | 200    |

    Examples: Member access
        | role   | resource     | status |
        | member | /users       | 200    |
        | member | /settings    | 403    |
```

## Common Patterns

### Fixture Chaining

```python
@given("a database with test data", target_fixture="db")
def given_db():
    return setup_test_db()

@given(parsers.parse("a user {name} in the database"), target_fixture="user")
def given_user_in_db(db, name):
    return db.create_user(name=name)

@when("the user is deleted", target_fixture="result")
def when_delete_user(db, user):
    return db.delete_user(user.id)
```

### Reusing Steps Across Features

Place in `tests/bdd/steps/conftest.py`:

```python
from pytest_bdd import given, parsers

@given(parsers.parse("the API is available at {base_url}"), target_fixture="api_url")
def given_api_available(base_url):
    return base_url
```

This step is now available to all feature step files without import.

## pytest-bdd-ng

For richer data table support (Gherkin Data Tables, Doc Strings), consider `pytest-bdd-ng`:

```bash
uv add --dev pytest-bdd-ng
```

Adds support for:
- Inline data tables in steps (not just Scenario Outline Examples)
- Doc String arguments (multi-line text blocks)
- Enhanced type converters
