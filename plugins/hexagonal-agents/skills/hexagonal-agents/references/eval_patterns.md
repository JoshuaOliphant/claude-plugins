# Evaluation Patterns for Hexagonal Agent Applications

This document provides comprehensive patterns for testing and evaluating hexagonal agent applications using `pydantic-evals`.

---

## Installation

```bash
pip install pydantic-evals
# or
uv add pydantic-evals

# Optional: for visualization
pip install 'pydantic-evals[logfire]'
```

---

## Evaluation Architecture

For hexagonal agent applications, evaluate three targets:

```
┌─────────────────────────────────────────────────────────────────┐
│                         EVALUATION TARGETS                       │
├─────────────────┬─────────────────────┬─────────────────────────┤
│   TOOL USAGE    │   STATE OUTCOME     │    UI QUALITY           │
│                 │                     │                         │
│ Did agent call  │ Is the data correct │ Does the HTML make      │
│ the right tools │ after the action?   │ sense for this context? │
│ with right      │                     │                         │
│ parameters?     │                     │                         │
└─────────────────┴─────────────────────┴─────────────────────────┘
```

**Grader Types:**

| Type | Use For | Example |
|------|---------|---------|
| **Code-based** | Deterministic checks | Tool called, state changed |
| **Model-based** | Subjective quality | UI appropriateness |
| **Human** | Calibration | Periodic review |

**Key Principle:** Grade outcomes, not paths. Don't require specific tool sequences—agents find creative valid solutions.

---

## Project Structure

```
your-app/
├── app/
│   ├── main.py
│   ├── agent.py
│   ├── tools.py
│   └── skills/ui.md
├── evals/
│   ├── __init__.py
│   ├── conftest.py           # Shared fixtures
│   ├── datasets/
│   │   ├── capability.py     # What can agent do?
│   │   └── regression.py     # Does it still work?
│   ├── evaluators/
│   │   ├── __init__.py
│   │   ├── tool_usage.py
│   │   ├── state.py
│   │   └── ui.py
│   └── test_agent.py         # Main runner
└── pyproject.toml
```

---

## Task Function

The task function wraps your agent for evaluation:

```python
# evals/test_agent.py
from dataclasses import dataclass
from typing import Any
from claude_agent_sdk import ClaudeSDKClient
from app.tools import create_tools_server
from app.agent import _build_system_prompt


@dataclass
class EvalResult:
    """Structured result from agent interaction."""
    html_output: str
    tool_calls: list[dict]
    final_state: dict
    turn_count: int
    total_tokens: int


async def run_agent_task(
    user_message: str,
    *,
    initial_state: dict | None = None,
) -> EvalResult:
    """
    Task function that runs the agent and returns structured results.
    """
    # Set up isolated state
    state = initial_state.copy() if initial_state else {}
    tool_calls_log = []

    # Create MCP server with test state (inject state)
    mcp_server = create_tools_server(state)

    # Wrap tools to log calls
    for name, tool_fn in list(mcp_server.tools.items()):
        async def logged_tool(args, _name=name, _fn=tool_fn):
            tool_calls_log.append({"name": _name, "args": args})
            return await _fn(args)
        mcp_server.tools[name] = logged_tool

    # Run agent
    client = ClaudeSDKClient(
        model="claude-sonnet-4-20250514",
        system=_build_system_prompt(),
        mcp_servers={"app_tools": mcp_server},
        allowed_tools=[f"mcp__app_tools__{t}" for t in mcp_server.tools.keys()],
    )

    await client.connect()
    await client.query(user_message)

    html_parts = []
    async for msg in client.receive_response():
        for block in msg.content:
            if hasattr(block, 'text'):
                html_parts.append(block.text)

    await client.disconnect()

    return EvalResult(
        html_output="\n".join(html_parts),
        tool_calls=tool_calls_log,
        final_state=state,
        turn_count=1,
        total_tokens=0,  # Would need to track from response
    )
```

---

## Evaluators

### Tool Usage Evaluators

```python
# evals/evaluators/tool_usage.py
from dataclasses import dataclass
from pydantic_evals.evaluators import Evaluator, EvaluatorContext


@dataclass
class ToolWasCalled(Evaluator):
    """Assert that a specific tool was called."""
    tool_name: str

    def evaluate(self, ctx: EvaluatorContext) -> float:
        tool_calls = ctx.output.tool_calls
        return 1.0 if any(c['name'] == self.tool_name for c in tool_calls) else 0.0


@dataclass
class ToolCalledWithParams(Evaluator):
    """Assert tool was called with specific parameters."""
    tool_name: str
    expected_params: dict

    def evaluate(self, ctx: EvaluatorContext) -> float:
        for call in ctx.output.tool_calls:
            if call['name'] == self.tool_name:
                actual = call['args']
                for key, value in self.expected_params.items():
                    if actual.get(key) != value:
                        return 0.0
                return 1.0
        return 0.0


@dataclass
class NoToolsCalled(Evaluator):
    """Assert that NO tools were called."""

    def evaluate(self, ctx: EvaluatorContext) -> float:
        return 1.0 if len(ctx.output.tool_calls) == 0 else 0.0


@dataclass
class ToolCallCount(Evaluator):
    """Assert tool call count is within range."""
    min_calls: int = 0
    max_calls: int = 10

    def evaluate(self, ctx: EvaluatorContext) -> float:
        count = len(ctx.output.tool_calls)
        return 1.0 if self.min_calls <= count <= self.max_calls else 0.0
```

### State Outcome Evaluators

```python
# evals/evaluators/state.py
from dataclasses import dataclass
from pydantic_evals.evaluators import Evaluator, EvaluatorContext


@dataclass
class StateContains(Evaluator):
    """Assert final state contains expected data."""
    collection: str
    match: dict

    def evaluate(self, ctx: EvaluatorContext) -> float:
        state = ctx.output.final_state
        items = state.get(self.collection, [])

        for item in items:
            if all(item.get(k) == v for k, v in self.match.items()):
                return 1.0
        return 0.0


@dataclass
class StateCountDelta(Evaluator):
    """Assert collection count changed by expected amount."""
    collection: str
    delta: int

    def evaluate(self, ctx: EvaluatorContext) -> float:
        initial_count = ctx.metadata.get('initial_count', {}).get(self.collection, 0)
        final_count = len(ctx.output.final_state.get(self.collection, []))
        actual_delta = final_count - initial_count
        return 1.0 if actual_delta == self.delta else 0.0


@dataclass
class StateUnchanged(Evaluator):
    """Assert state was NOT modified."""

    def evaluate(self, ctx: EvaluatorContext) -> float:
        initial = ctx.metadata.get('initial_state', {})
        final = ctx.output.final_state
        return 1.0 if initial == final else 0.0


@dataclass
class ItemDeleted(Evaluator):
    """Assert a specific item was deleted."""
    collection: str
    item_id: str

    def evaluate(self, ctx: EvaluatorContext) -> float:
        items = ctx.output.final_state.get(self.collection, [])
        for item in items:
            if item.get('id') == self.item_id:
                return 0.0  # Item still exists
        return 1.0  # Item deleted
```

### UI Quality Evaluators

```python
# evals/evaluators/ui.py
from dataclasses import dataclass
from pydantic_evals.evaluators import Evaluator, EvaluatorContext, LLMJudge


@dataclass
class ContainsHTMXAttributes(Evaluator):
    """Check interactive elements have HTMX attributes."""

    def evaluate(self, ctx: EvaluatorContext) -> float:
        html = ctx.output.html_output

        has_interactive = '<button' in html or '<form' in html
        has_htmx = 'hx-post=' in html or 'hx-get=' in html

        if not has_interactive:
            return 1.0  # No interactive elements needed

        return 1.0 if has_htmx else 0.0


@dataclass
class NoMarkdownFences(Evaluator):
    """Assert output doesn't contain markdown code fences."""

    def evaluate(self, ctx: EvaluatorContext) -> float:
        html = ctx.output.html_output
        if '```html' in html or html.startswith('```'):
            return 0.0
        return 1.0


@dataclass
class ContainsText(Evaluator):
    """Assert output contains specific text."""
    text: str

    def evaluate(self, ctx: EvaluatorContext) -> float:
        return 1.0 if self.text in ctx.output.html_output else 0.0


# LLM-based evaluator for subjective quality
UIAppropriatenessJudge = LLMJudge(
    rubric="""
    Evaluate whether the HTML output is appropriate for the user's request.

    Score 1.0 if:
    - The UI clearly addresses the user's intent
    - Interactive elements have correct HTMX attributes
    - The layout matches the action type (list for viewing, form for creating)
    - Success/error states are clear when relevant

    Score 0.5 if:
    - The UI partially addresses the request but is missing elements
    - HTMX attributes present but potentially incorrect

    Score 0.0 if:
    - The UI doesn't match the request at all
    - Critical interactive elements are missing
    - Raw data dump instead of formatted UI
    """,
    model="claude-haiku-3-5-20241022",
)


HTMLValidityJudge = LLMJudge(
    rubric="""
    Check if the HTML output is valid and well-formed.

    Score 1.0 if:
    - Valid HTML structure
    - All tags properly closed
    - No markdown code fences
    - Uses Tailwind classes appropriately

    Score 0.0 if:
    - Malformed HTML
    - Wrapped in markdown code fences
    - Contains raw JSON or error traces
    """,
    model="claude-haiku-3-5-20241022",
)
```

---

## Datasets

### Capability Dataset

```python
# evals/datasets/capability.py
from pydantic_evals import Case, Dataset
from evals.evaluators.tool_usage import ToolWasCalled, ToolCalledWithParams
from evals.evaluators.state import StateContains, StateCountDelta
from evals.evaluators.ui import ContainsHTMXAttributes, UIAppropriatenessJudge

capability_cases = [
    # CREATE operations
    Case(
        name="create_natural_language",
        inputs="Add a book called The Hobbit by Tolkien",
        metadata={"category": "create", "initial_state": {"books": []}},
        evaluators=[
            ToolWasCalled(tool_name="create_book"),
            ToolCalledWithParams(
                tool_name="create_book",
                expected_params={"name": "The Hobbit"}
            ),
            StateCountDelta(collection="books", delta=1),
        ],
    ),

    # READ operations
    Case(
        name="list_empty_state",
        inputs="Show me my books",
        metadata={
            "category": "read",
            "initial_state": {"books": []},
        },
        evaluators=[
            ToolWasCalled(tool_name="list_books"),
            ContainsHTMXAttributes(),
        ],
    ),

    Case(
        name="list_with_items",
        inputs="What books do I have?",
        metadata={
            "category": "read",
            "initial_state": {
                "books": [
                    {"id": "1", "name": "Dune", "author": "Frank Herbert"},
                    {"id": "2", "name": "Foundation", "author": "Isaac Asimov"},
                ]
            },
        },
        evaluators=[
            ToolWasCalled(tool_name="list_books"),
            UIAppropriatenessJudge,
        ],
    ),

    # UPDATE operations
    Case(
        name="update_item",
        inputs="Change the status of book 1 to completed",
        metadata={
            "category": "update",
            "initial_state": {
                "books": [{"id": "1", "name": "Dune", "status": "reading"}]
            },
        },
        evaluators=[
            ToolWasCalled(tool_name="update_book"),
            StateContains(collection="books", match={"id": "1", "status": "completed"}),
        ],
    ),

    # DELETE operations
    Case(
        name="delete_item",
        inputs="Delete book 1",
        metadata={
            "category": "delete",
            "initial_state": {
                "books": [{"id": "1", "name": "Dune"}]
            },
        },
        evaluators=[
            ToolWasCalled(tool_name="delete_book"),
            StateCountDelta(collection="books", delta=-1),
        ],
    ),
]

capability_dataset = Dataset(
    cases=capability_cases,
    evaluators=[
        ContainsHTMXAttributes(),  # All responses need HTMX
    ],
)
```

### Regression Dataset

```python
# evals/datasets/regression.py
from pydantic_evals import Case, Dataset
from evals.evaluators.ui import NoMarkdownFences, UIAppropriatenessJudge

regression_cases = [
    Case(
        name="basic_greeting",
        inputs="Hello",
        metadata={"category": "conversation"},
        evaluators=[
            NoMarkdownFences(),
        ],
    ),

    Case(
        name="handles_gibberish",
        inputs="asdf jkl; qwerty",
        metadata={"category": "error_handling"},
        evaluators=[
            NoMarkdownFences(),
            UIAppropriatenessJudge,
        ],
    ),

    Case(
        name="empty_message_handling",
        inputs="",
        metadata={"category": "error_handling"},
        evaluators=[
            NoMarkdownFences(),
        ],
    ),
]

regression_dataset = Dataset(cases=regression_cases)
```

---

## Running Evaluations

### Basic Run

```python
# evals/test_agent.py
import asyncio
from evals.datasets.capability import capability_dataset
from evals.datasets.regression import regression_dataset


async def main():
    # Run capability eval
    print("=" * 60)
    print("CAPABILITY EVALUATION")
    print("=" * 60)

    capability_report = await capability_dataset.evaluate(run_agent_task)
    capability_report.print(
        include_input=True,
        include_output=False,
        include_durations=True,
    )

    # Run regression eval
    print("\n" + "=" * 60)
    print("REGRESSION EVALUATION")
    print("=" * 60)

    regression_report = await regression_dataset.evaluate(run_agent_task)
    regression_report.print()

    # Check regression pass rate
    if regression_report.summary.pass_rate < 1.0:
        print(f"\n⚠️  REGRESSION: {regression_report.summary.pass_rate:.1%}")
        return 1

    print(f"\n✅ All regressions passing")
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
```

### Multiple Trials

```python
# Run each case 3 times for consistency
report = await dataset.evaluate(
    run_agent_task,
    max_concurrency=5,
    num_trials=3,
)

# Analyze consistency
for result in report.results:
    scores = [trial.score for trial in result.trials]
    avg = sum(scores) / len(scores)
    consistent = all(s >= 0.8 for s in scores)
    print(f"{result.case_name}: avg={avg:.2f}, consistent={consistent}")
```

### Debugging Failed Cases

```python
for result in report.results:
    if result.score < 0.8:
        print(f"=== FAILED: {result.case_name} ===")
        print(f"Input: {result.input}")
        print(f"Tool calls: {result.output.tool_calls}")
        print(f"HTML (first 500): {result.output.html_output[:500]}")
        print(f"Scores: {result.evaluator_scores}")
```

---

## CI/CD Integration

```yaml
# .github/workflows/evals.yml
name: Agent Evals

on:
  push:
    branches: [main]
  pull_request:

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pydantic-evals

      - name: Run regression evals
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python -m evals.test_agent --regression-only

      - name: Run capability evals (main only)
        if: github.ref == 'refs/heads/main'
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python -m evals.test_agent --all
```

---

## Best Practices

### 1. Start from Real Failures

Convert bugs into test cases immediately:

```python
# Bug #123: Agent creates duplicate items
Case(
    name="bug_123_no_duplicates",
    inputs="Add Dune. Add Dune again.",
    evaluators=[
        StateCountDelta(collection="books", delta=1),  # Should only add once
    ],
)
```

### 2. Balance Positive and Negative Cases

```python
# Positive: agent SHOULD search
Case(name="should_search", inputs="Find books about dragons", ...)

# Negative: agent should NOT search
Case(name="should_not_search", inputs="Thanks!", ...)
```

### 3. Graduate Passing Tests

When capability eval hits 95%+ consistently, move to regression:

```python
# Capability → Regression promotion
# 1. Case passes 95%+ over 10 runs
# 2. Move to regression_cases
# 3. Now must stay at 100%
```

### 4. Track Metrics Over Time

```python
metrics = {
    'avg_turns': sum(r.output.turn_count for r in report.results) / len(report.results),
    'avg_tokens': sum(r.output.total_tokens for r in report.results) / len(report.results),
    'pass_rate': report.summary.pass_rate,
    'timestamp': datetime.now().isoformat(),
}

# Save for trending
with open(f"evals/results/{datetime.now().date()}.json", "w") as f:
    json.dump(metrics, f)
```

---

## Summary

| Principle | Implementation |
|-----------|----------------|
| Grade outcomes, not paths | Use state evaluators, not tool sequence checks |
| Combine grader types | Code for deterministic, LLM for subjective |
| Run multiple trials | Use `num_trials` for consistency checking |
| Start with failures | Convert bugs to test cases immediately |
| Balance positive/negative | Test "should do" and "should NOT do" |
| Track metrics | Log turns, tokens, latency over time |

**Start simple:** 20-50 cases from real usage. Grow as you find edge cases.
