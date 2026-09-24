# Gherkin feature files

When the project runs a BDD suite, the acceptance criteria also become `.feature` files, so the
spec runs as tests. Spec writes the feature files; `compost:build` writes the step definitions
while it fits each criterion's test into the suite.

Write feature files only when the project wants them: `docs/agents/testing.md` names a BDD runner,
or one is already a dependency (pytest-bdd in `pyproject.toml`, `@cucumber/cucumber`, godog,
cucumber-ruby). Otherwise the markdown criteria are the spec and build names tests after AC-N.

## Mapping

| Spec | Gherkin |
|---|---|
| Parent issue title | `Feature:` name |
| The user story | The feature's description lines |
| AC-N | A `Scenario:`, tagged `@ac-N` |
| **Given** / **When** / **Then** | `Given` / `When` / `Then` |
| Indented `and` lines | `And` |
| A scenario outline with its table | `Scenario Outline:` with `Examples:` |
| A Given shared by every scenario in the file | `Background:` |

One feature file per user story keeps the story's why next to its scenarios. The `@ac-N` tag is
how verify finds the test for each criterion, so every scenario carries exactly one.

```gherkin
Feature: Customers cancel unshipped orders
    As a customer, I want to cancel an order before it ships,
    so that I am not charged for something I no longer want.

    Background:
        Given a customer signed in to their account

    @ac-1
    Scenario: Customer cancels a pending order
        Given an order in pending with no shipped lines
        When the customer cancels it
        Then the order moves to cancelled
        And the customer receives the cancellation email

    @ac-9
    Scenario Outline: Cancellation is refused for orders past the window
        Given an order in <state>
        When the customer cancels it
        Then the page shows "<message>"
        And the order stays in <state>

        Examples:
            | state     | message                                        |
            | shipped   | This order has shipped. Start a return instead |
            | delivered | This order has shipped. Start a return instead |
```

## Where the files go

Follow the layout the project already uses. With no layout yet, use the runner's convention:

- **pytest-bdd (Python):** `tests/bdd/features/<story-slug>.feature`, with step modules under
  `tests/bdd/steps/` and `bdd_features_base_dir = "tests/bdd/features/"` under
  `[tool.pytest-bdd]` in `pyproject.toml`. Add the runner with `uv add --dev pytest-bdd` if the
  test convention calls for it and it is missing.
- **cucumber-js:** `features/<story-slug>.feature`, steps in `features/step_definitions/`.
- **godog:** `features/<story-slug>.feature` beside the package under test.

Check that the runner collects every scenario (`uv run pytest tests/bdd --collect-only` for
pytest-bdd). A scenario that is not collected is not a test.

## Step phrasing

Write steps so they read as the domain, and so one step definition can serve many scenarios:
"an order in pending" rather than "an order with status column equal to 1". Quote literal values
the step must match (`"<message>"`) so the step parser can extract them.
