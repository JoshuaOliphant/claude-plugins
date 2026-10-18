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
│   ├── task.py               # run_agent_task + AgentInput
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
# evals/task.py
import asyncio
import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

import app.tools
from app.agent import _build_system_prompt
from app.tools import create_tools_server

SERVER = "app_tools"
TOOL_PREFIX = f"mcp__{SERVER}__"

# The tools read the module-global DATA_FILE, so runs that overlap (evaluate()
# runs cases concurrently) would share one store. Run them one at a time.
_store_lock = asyncio.Lock()


@dataclass
class AgentInput:
    """A case's inputs: the message plus the state to seed before the run.

    pydantic-evals hands the task only `case.inputs`, never `case.metadata`, so the
    seed has to travel here. Evaluators read it back from `ctx.inputs`, which keeps
    one copy of it for both the run and the assertions.
    """
    message: str
    initial_state: dict = field(default_factory=dict)


@dataclass
class EvalResult:
    """Structured result from agent interaction."""
    html_output: str
    tool_calls: list[dict]
    final_state: dict
    turn_count: int
    total_tokens: int


async def run_agent_task(inputs: AgentInput) -> EvalResult:
    """
    Task function that runs the agent and returns structured results.
    """
    async with _store_lock:
        original_data_file = app.tools.DATA_FILE
        with tempfile.TemporaryDirectory() as tmp:
            # Isolate state: point the tools' JSON store at a seeded temp file
            data_file = Path(tmp) / "data.json"
            data_file.write_text(json.dumps(inputs.initial_state))
            app.tools.DATA_FILE = data_file
            try:
                html_parts, tool_calls, result = await _converse(inputs.message)
            finally:
                app.tools.DATA_FILE = original_data_file
            final_state = json.loads(data_file.read_text())

    usage = (result.usage if result else None) or {}
    return EvalResult(
        html_output="\n".join(html_parts),
        tool_calls=tool_calls,
        final_state=final_state,
        turn_count=result.num_turns if result else 0,
        # input_tokens excludes cached prompt tokens, so count those too
        total_tokens=sum(usage.get(k, 0) for k in (
            "input_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
            "output_tokens",
        )),
    )


async def _converse(
    user_message: str,
) -> tuple[list[str], list[dict], ResultMessage | None]:
    options = ClaudeAgentOptions(
        model="claude-sonnet-5-5",
        system_prompt=_build_system_prompt(),
        mcp_servers={SERVER: create_tools_server()},
        allowed_tools=[f"mcp__{SERVER}"],  # server-level rule: every tool on app_tools
    )

    html_parts: list[str] = []
    tool_calls: list[dict] = []
    result: ResultMessage | None = None

    async with ClaudeSDKClient(options=options) as client:
        await client.query(user_message)
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        html_parts.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        # Log calls from the stream; the server's tools are not wrappable
                        tool_calls.append({
                            "name": block.name.removeprefix(TOOL_PREFIX),
                            "args": block.input,
                        })
            elif isinstance(msg, ResultMessage):
                result = msg

    return html_parts, tool_calls, result
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
        initial_count = len(ctx.inputs.initial_state.get(self.collection, []))
        final_count = len(ctx.output.final_state.get(self.collection, []))
        actual_delta = final_count - initial_count
        return 1.0 if actual_delta == self.delta else 0.0


@dataclass
class StateUnchanged(Evaluator):
    """Assert state was NOT modified."""

    def evaluate(self, ctx: EvaluatorContext) -> float:
        initial = ctx.inputs.initial_state
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
    model="claude-haiku-5-5",
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
    model="claude-haiku-5-5",
)
```

---

## Datasets

### Capability Dataset

```python
# evals/datasets/capability.py
from pydantic_evals import Case, Dataset
from evals.task import AgentInput
from evals.evaluators.tool_usage import ToolWasCalled, ToolCalledWithParams
from evals.evaluators.state import StateContains, StateCountDelta
from evals.evaluators.ui import ContainsHTMXAttributes, UIAppropriatenessJudge

capability_cases = [
    # CREATE operations
    Case(
        name="create_natural_language",
        inputs=AgentInput(
            "Add a book called The Hobbit by Tolkien",
            initial_state={"books": []},
        ),
        metadata={"category": "create"},
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
        inputs=AgentInput("Show me my books", initial_state={"books": []}),
        metadata={"category": "read"},
        evaluators=[
            ToolWasCalled(tool_name="list_books"),
            ContainsHTMXAttributes(),
        ],
    ),

    Case(
        name="list_with_items",
        inputs=AgentInput(
            "What books do I have?",
            initial_state={
                "books": [
                    {"id": "1", "name": "Dune", "author": "Frank Herbert"},
                    {"id": "2", "name": "Foundation", "author": "Isaac Asimov"},
                ]
            },
        ),
        metadata={"category": "read"},
        evaluators=[
            ToolWasCalled(tool_name="list_books"),
            UIAppropriatenessJudge,
        ],
    ),

    # UPDATE operations
    Case(
        name="update_item",
        inputs=AgentInput(
            "Change the status of book 1 to completed",
            initial_state={
                "books": [{"id": "1", "name": "Dune", "status": "reading"}]
            },
        ),
        metadata={"category": "update"},
        evaluators=[
            ToolWasCalled(tool_name="update_book"),
            StateContains(collection="books", match={"id": "1", "status": "completed"}),
        ],
    ),

    # DELETE operations
    Case(
        name="delete_item",
        inputs=AgentInput(
            "Delete book 1",
            initial_state={"books": [{"id": "1", "name": "Dune"}]},
        ),
        metadata={"category": "delete"},
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
from evals.task import AgentInput
from evals.evaluators.ui import NoMarkdownFences, UIAppropriatenessJudge

regression_cases = [
    Case(
        name="basic_greeting",
        inputs=AgentInput("Hello"),
        metadata={"category": "conversation"},
        evaluators=[
            NoMarkdownFences(),
        ],
    ),

    Case(
        name="handles_gibberish",
        inputs=AgentInput("asdf jkl; qwerty"),
        metadata={"category": "error_handling"},
        evaluators=[
            NoMarkdownFences(),
            UIAppropriatenessJudge,
        ],
    ),

    Case(
        name="empty_message_handling",
        inputs=AgentInput(""),
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
from evals.task import run_agent_task
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

pass@k means at least one of k trials succeeds (fits tasks where one good answer is enough, like exploratory generation); pass^k means all k succeed (fits user-facing behavior that must be reliable every time).

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
    inputs=AgentInput("Add Dune. Add Dune again.", initial_state={"books": []}),
    evaluators=[
        StateCountDelta(collection="books", delta=1),  # Should only add once
    ],
)
```

### 2. Balance Positive and Negative Cases

```python
# Positive: agent SHOULD search
Case(name="should_search", inputs=AgentInput("Find books about dragons"), ...)

# Negative: agent should NOT search
Case(name="should_not_search", inputs=AgentInput("Thanks!"), ...)
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
