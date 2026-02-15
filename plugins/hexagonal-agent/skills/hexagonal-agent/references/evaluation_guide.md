# Evaluation Guide for Hexagonal Agent Applications

This guide shows how to systematically test and evaluate your hexagonal agent application using `pydantic-evals`. It applies Anthropic's agent evaluation principles to your conversational agent built with the Anthropic Agent SDK.

---

## Why Evaluate?

Without evals, you're flying blind:
- Can't tell if changes made things better or worse
- Catch issues only when users complain
- Can't confidently upgrade models or change prompts

With evals, you get:
- Regression protection (did we break something?)
- Capability tracking (what can the agent do?)
- Metrics over time (latency, token usage, success rate)

**Start with 20-50 simple tasks from real failures.** Don't wait for the "perfect" suite.

---

## Installation

```bash
pip install pydantic-evals
# Optional: for visualization
pip install 'pydantic-evals[logfire]'
```

---

## Evaluation Architecture

For a hexagonal agent app, you evaluate three things:

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

### Grader Types

| Type | Use For | Example |
|------|---------|---------|
| **Code-based** | Deterministic checks | Tool was called, state changed correctly |
| **Model-based** | Subjective quality | UI appropriateness, tone, completeness |
| **Human** | Calibration | Periodic review of LLM-graded results |

**Key principle:** Grade the outcome, not the path. Don't require specific tool sequences—agents find creative valid solutions.

---

## Project Structure

```
your-app/
├── main.py              # FastAPI app
├── tools.py             # MCP tools
├── skill.py             # Skill file content
├── evals/
│   ├── __init__.py
│   ├── conftest.py      # Shared fixtures
│   ├── datasets/
│   │   ├── core.yaml         # Core functionality cases
│   │   └── regression.yaml   # Regression test cases
│   ├── evaluators/
│   │   ├── __init__.py
│   │   ├── tool_usage.py     # Tool call evaluators
│   │   ├── state.py          # State outcome evaluators
│   │   └── ui.py             # UI quality evaluators
│   └── test_agent.py    # Main eval runner
└── requirements.txt
```

---

## Core Concepts

### Dataset & Cases

A **Dataset** is a collection of test **Cases**. Each case has:
- `inputs`: The user message
- `expected_output`: What success looks like (optional)
- `metadata`: Context for evaluators
- `evaluators`: Case-specific checks

```python
# evals/datasets/core.yaml
cases:
  - name: "add_book_complete"
    inputs: "Add 'The Pragmatic Programmer' by David Thomas"
    expected_output:
      tool_called: "add_book"
      state_change:
        books_count_delta: 1
        book_exists:
          title: "The Pragmatic Programmer"
          author: "David Thomas"
    metadata:
      category: "create"

  - name: "list_empty_state"
    inputs: "Show me my books"
    expected_output:
      shows_empty_state: true
    metadata:
      category: "read"
      initial_state: "empty"
```

### Evaluators

Evaluators score the agent's performance:

```python
from dataclasses import dataclass
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

@dataclass
class ToolWasCalled(Evaluator):
    """Check if a specific tool was called."""
    tool_name: str

    def evaluate(self, ctx: EvaluatorContext) -> float:
        # Access tool calls from the trace/transcript
        tool_calls = ctx.metadata.get('tool_calls', [])
        for call in tool_calls:
            if call['name'] == self.tool_name:
                return 1.0
        return 0.0
```

---

## Building Your Eval Suite

### Step 1: Create the Task Function

The task function wraps your agent interaction:

```python
# evals/test_agent.py
import json
from dataclasses import dataclass
from typing import Any

from anthropic_sdk import ClaudeSDKClient

# Your app's imports
from tools import create_mcp_server
from skill import SKILL_CONTENT


@dataclass
class EvalDependencies:
    """Dependencies injected into each eval run."""
    db: dict  # In-memory state for testing


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

    This is what pydantic-evals will call for each test case.
    """
    # Set up isolated state for this eval run
    state = initial_state or {}
    tool_calls_log = []

    # Create MCP server with test state
    mcp_server = create_mcp_server(state)

    # Wrap tools to log calls
    original_tools = mcp_server.tools
    def logging_tool_wrapper(tool_fn, tool_name):
        async def wrapper(*args, **kwargs):
            tool_calls_log.append({
                'name': tool_name,
                'args': kwargs,
            })
            return await tool_fn(*args, **kwargs)
        return wrapper

    for name, tool in original_tools.items():
        mcp_server.tools[name] = logging_tool_wrapper(tool, name)

    # Run agent
    client = ClaudeSDKClient(
        model="claude-sonnet-4-20250514",
        system=SKILL_CONTENT,
        mcp_servers=[mcp_server],
    )

    client.add_user_message(user_message)
    response = await client.receive_response()

    return EvalResult(
        html_output=response.content,
        tool_calls=tool_calls_log,
        final_state=state,
        turn_count=len(client.messages) // 2,
        total_tokens=response.usage.total_tokens,
    )
```

### Step 2: Define Evaluators

**Tool Usage Evaluators**

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
                # Check if expected params are subset of actual
                actual = call['args']
                for key, value in self.expected_params.items():
                    if actual.get(key) != value:
                        return 0.0
                return 1.0
        return 0.0


@dataclass
class NoToolsCalled(Evaluator):
    """Assert that NO tools were called (agent answered from context)."""

    def evaluate(self, ctx: EvaluatorContext) -> float:
        return 1.0 if len(ctx.output.tool_calls) == 0 else 0.0


@dataclass
class ToolCallCount(Evaluator):
    """Assert tool call count is within range."""
    min_calls: int = 0
    max_calls: int = 10

    def evaluate(self, ctx: EvaluatorContext) -> float:
        count = len(ctx.output.tool_calls)
        if self.min_calls <= count <= self.max_calls:
            return 1.0
        return 0.0
```

**State Outcome Evaluators**

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
    """Assert state was NOT modified (read-only operation)."""

    def evaluate(self, ctx: EvaluatorContext) -> float:
        initial = ctx.metadata.get('initial_state', {})
        final = ctx.output.final_state
        return 1.0 if initial == final else 0.0
```

**UI Quality Evaluators (LLM-as-Judge)**

```python
# evals/evaluators/ui.py
from dataclasses import dataclass
from pydantic_evals.evaluators import LLMJudge


# LLM-based evaluator for subjective UI quality
UIAppropriatenessJudge = LLMJudge(
    rubric="""
    Evaluate whether the HTML output is appropriate for the user's request.

    Score 1.0 if:
    - The UI clearly addresses the user's intent
    - Interactive elements (buttons, forms) have correct HTMX attributes
    - The layout matches the action type (list for viewing, form for creating, etc.)
    - Success/error states are clear when relevant

    Score 0.5 if:
    - The UI partially addresses the request but is missing elements
    - HTMX attributes present but potentially incorrect

    Score 0.0 if:
    - The UI doesn't match the request at all
    - Critical interactive elements are missing or broken
    - Raw data dump instead of formatted UI
    """,
    model="claude-haiku-3-5-20241022",  # Use cheaper model for grading
)


HTMLValidityJudge = LLMJudge(
    rubric="""
    Check if the HTML output is valid and well-formed.

    Score 1.0 if:
    - Valid HTML structure
    - All tags properly closed
    - No markdown code fences (```html)
    - Uses appropriate Tailwind classes

    Score 0.0 if:
    - Malformed HTML
    - Wrapped in markdown code fences
    - Contains raw JSON or error traces
    """,
    model="claude-haiku-3-5-20241022",
)


@dataclass
class ContainsHTMXAttributes(Evaluator):
    """Check that interactive elements have HTMX attributes."""

    def evaluate(self, ctx: EvaluatorContext) -> float:
        html = ctx.output.html_output

        # Quick heuristic: if there are buttons/forms, check for hx-post
        has_interactive = '<button' in html or '<form' in html
        has_htmx = 'hx-post=' in html or 'hx-get=' in html

        if not has_interactive:
            return 1.0  # No interactive elements needed

        return 1.0 if has_htmx else 0.0
```

### Step 3: Create Datasets

```python
# evals/datasets/core.py
from pydantic_evals import Case, Dataset
from evals.evaluators.tool_usage import ToolWasCalled, ToolCalledWithParams
from evals.evaluators.state import StateContains, StateCountDelta
from evals.evaluators.ui import UIAppropriatenessJudge, ContainsHTMXAttributes


# ============================================================
# CAPABILITY EVAL: What can the agent do?
# Start these at low pass rates, hill-climb to improve
# ============================================================

capability_cases = [
    # CREATE operations
    Case(
        name="add_book_natural_language",
        inputs="I just finished reading 1984 by George Orwell, can you add it?",
        metadata={"category": "create", "initial_state": {}},
        evaluators=[
            ToolWasCalled(tool_name="add_book"),
            ToolCalledWithParams(
                tool_name="add_book",
                expected_params={"title": "1984", "author": "George Orwell"}
            ),
            StateCountDelta(collection="books", delta=1),
        ],
    ),

    Case(
        name="add_book_with_status",
        inputs="Add 'Clean Code' by Robert Martin to my reading list",
        metadata={"category": "create"},
        evaluators=[
            ToolWasCalled(tool_name="add_book"),
            StateContains(
                collection="books",
                match={"title": "Clean Code", "status": "want_to_read"}
            ),
        ],
    ),

    # READ operations
    Case(
        name="list_books_empty",
        inputs="What books do I have?",
        metadata={
            "category": "read",
            "initial_state": {"books": []},
        },
        evaluators=[
            ToolWasCalled(tool_name="list_books"),
            ContainsHTMXAttributes(),  # Should have "add first book" button
        ],
    ),

    Case(
        name="list_books_populated",
        inputs="Show my reading list",
        metadata={
            "category": "read",
            "initial_state": {
                "books": [
                    {"id": 1, "title": "Dune", "author": "Frank Herbert", "status": "reading"},
                    {"id": 2, "title": "Foundation", "author": "Isaac Asimov", "status": "finished"},
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
        name="update_status",
        inputs="I finished reading Dune",
        metadata={
            "category": "update",
            "initial_state": {
                "books": [{"id": 1, "title": "Dune", "author": "Frank Herbert", "status": "reading"}]
            },
        },
        evaluators=[
            ToolWasCalled(tool_name="update_book_status"),
            StateContains(collection="books", match={"id": 1, "status": "finished"}),
        ],
    ),

    Case(
        name="rate_book",
        inputs="Give Foundation 5 stars",
        metadata={
            "category": "update",
            "initial_state": {
                "books": [{"id": 1, "title": "Foundation", "author": "Isaac Asimov", "status": "finished"}]
            },
        },
        evaluators=[
            ToolWasCalled(tool_name="rate_book"),
            StateContains(collection="books", match={"id": 1, "rating": 5}),
        ],
    ),
]

capability_dataset = Dataset(
    cases=capability_cases,
    evaluators=[
        ContainsHTMXAttributes(),  # All responses should have proper HTMX
    ],
)


# ============================================================
# REGRESSION EVAL: Does it still work?
# These should have ~100% pass rate
# ============================================================

regression_cases = [
    Case(
        name="basic_greeting",
        inputs="Hello",
        metadata={"category": "conversation"},
        evaluators=[
            # Should respond conversationally, not call tools
            # NoToolsCalled(),  # Optional: depends on your design
        ],
    ),

    Case(
        name="handles_gibberish",
        inputs="asdf jkl; qwerty",
        metadata={"category": "error_handling"},
        evaluators=[
            UIAppropriatenessJudge,  # Should handle gracefully
        ],
    ),
]

regression_dataset = Dataset(cases=regression_cases)
```

### Step 4: Run Evaluations

```python
# evals/test_agent.py (continued)
import asyncio
from evals.datasets.core import capability_dataset, regression_dataset


async def main():
    # Run capability eval
    print("=" * 60)
    print("CAPABILITY EVALUATION")
    print("=" * 60)

    capability_report = await capability_dataset.evaluate(run_agent_task)
    capability_report.print(
        include_input=True,
        include_output=False,  # HTML too verbose
        include_durations=True,
    )

    # Run regression eval
    print("\n" + "=" * 60)
    print("REGRESSION EVALUATION")
    print("=" * 60)

    regression_report = await regression_dataset.evaluate(run_agent_task)
    regression_report.print()

    # Check regression pass rate
    regression_pass_rate = regression_report.summary.pass_rate
    if regression_pass_rate < 1.0:
        print(f"\n⚠️  REGRESSION DETECTED: {regression_pass_rate:.1%} pass rate")
        return 1

    print(f"\n✅ All regressions passing")
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
```

---

## Advanced Patterns

### Multiple Trials for Non-Determinism

Agent behavior varies between runs. Run multiple trials:

```python
from pydantic_evals import Dataset

# Run each case 3 times
report = await dataset.evaluate(
    run_agent_task,
    max_concurrency=5,
    num_trials=3,  # Run each case 3 times
)

# Analyze consistency
for case_result in report.results:
    scores = [trial.score for trial in case_result.trials]
    avg_score = sum(scores) / len(scores)
    all_passed = all(s >= 0.8 for s in scores)

    print(f"{case_result.case_name}: avg={avg_score:.2f}, consistent={all_passed}")
```

**pass@k**: At least one of k trials succeeds (good for "can it do this at all?")
**pass^k**: All k trials succeed (good for "is it reliable?")

### Span-Based Evaluation (Tool Call Traces)

For deeper inspection of agent behavior:

```python
from pydantic_evals.evaluators import SpanEvaluator

class ToolSequenceEvaluator(SpanEvaluator):
    """Evaluate the sequence of tool calls in the trace."""

    expected_sequence: list[str]

    def evaluate_spans(self, spans) -> float:
        tool_spans = [s for s in spans if s.name.startswith('tool:')]
        actual_sequence = [s.name.replace('tool:', '') for s in tool_spans]

        # Flexible matching: expected tools appear in order (not necessarily consecutive)
        expected_idx = 0
        for tool in actual_sequence:
            if expected_idx < len(self.expected_sequence):
                if tool == self.expected_sequence[expected_idx]:
                    expected_idx += 1

        return expected_idx / len(self.expected_sequence) if self.expected_sequence else 1.0
```

### Metrics Tracking

Track performance over time:

```python
from pydantic_evals import Dataset

report = await dataset.evaluate(run_agent_task)

# Extract metrics
metrics = {
    'avg_turns': sum(r.output.turn_count for r in report.results) / len(report.results),
    'avg_tokens': sum(r.output.total_tokens for r in report.results) / len(report.results),
    'avg_latency_ms': sum(r.duration_ms for r in report.results) / len(report.results),
    'pass_rate': report.summary.pass_rate,
}

print(f"Metrics: {metrics}")

# Save for trending
import json
from datetime import datetime

with open(f"evals/results/{datetime.now().isoformat()}.json", "w") as f:
    json.dump(metrics, f)
```

### CI/CD Integration

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

      - name: Run capability evals (optional, on main only)
        if: github.ref == 'refs/heads/main'
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python -m evals.test_agent --all
```

---

## Eval Development Workflow

### 1. Start from Failures

When you find a bug or user reports an issue:

```python
# Convert the bug into a test case
Case(
    name="bug_123_double_add",
    inputs="Add Dune. Add Dune again.",  # User reported duplicate books
    metadata={"bug_id": "123", "category": "edge_case"},
    evaluators=[
        StateCountDelta(collection="books", delta=1),  # Should only add once
    ],
)
```

### 2. Balance Your Dataset

Test both positive and negative cases:

```python
# Positive: agent SHOULD search
Case(name="should_search", inputs="What books have I rated 5 stars?", ...)

# Negative: agent should NOT search (answer from context)
Case(name="should_not_search", inputs="Thanks!", ...)
```

### 3. Iterate on Graders

If scores don't match your intuition, the grader might be wrong:

```python
# Read transcripts to debug
for result in report.results:
    if result.score < 0.8:
        print(f"=== FAILED: {result.case_name} ===")
        print(f"Input: {result.input}")
        print(f"Tool calls: {result.output.tool_calls}")
        print(f"HTML (first 500 chars): {result.output.html_output[:500]}")
        print(f"Scores: {result.evaluator_scores}")
```

### 4. Graduate Capability → Regression

When a capability eval hits 95%+ pass rate consistently, move it to regression suite:

```python
# Before: in capability_dataset (hill-climbing)
# After: in regression_dataset (must stay at 100%)
```

---

## Summary

| Principle | Implementation |
|-----------|----------------|
| Grade outcomes, not paths | Use state evaluators, not tool sequence checks |
| Combine grader types | Code-based for deterministic, LLM for subjective |
| Run multiple trials | Use `num_trials` parameter for consistency |
| Start with real failures | Convert bugs to test cases immediately |
| Balance positive/negative | Test both "should do X" and "should NOT do X" |
| Track metrics | Log turns, tokens, latency over time |

**Start simple:** 20-50 cases from real usage and failures. Grow the suite as you find edge cases.

**Read transcripts:** The only way to know if your evals are actually measuring what matters.
