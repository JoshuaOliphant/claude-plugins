# AI Developer Workflows (ADWs): Core Principles

## What Are ADWs?

**AI Developer Workflows (ADWs)** are executable scripts that combine deterministic code with non-deterministic, compute-scalable AI agents to perform complex development tasks programmatically.

Instead of directly modifying code yourself, you **template your engineering patterns** and **teach agents how to operate your codebase**. This allows you to scale impact by scaling compute, not just effort.

## The Two-Layer Architecture

### Agentic Layer
**Purpose**: Template engineering patterns and teach agents how to operate

**Components**:
- `adws/` - AI Developer Workflow scripts and modules
- `.claude/` - Slash commands, skills, hooks, agent configurations
- `specs/` - Implementation plans and specifications
- `agents/` - Agent execution outputs (observability)

**Role**: Provides the programmatic interface for AI-driven development

### Application Layer
**Purpose**: The actual application code that agents operate on

**Components**:
- `apps/`, `src/`, `lib/`, etc. - Your application code
- `tests/` - Your test suites
- Application-specific configuration and resources

**Role**: What the agents modify, test, and deploy

## The 12 Leverage Points of Agentic Coding

### In Agent (Core Four)
These directly control agent behavior during execution:

1. **Context** - What information the agent has access to
2. **Model** - Which AI model processes the prompt (Sonnet vs Opus)
3. **Prompt** - The specific instructions given to the agent
4. **Tools** - What actions the agent can take (Read, Write, Bash, etc.)

### Through Agent (Structural Eight)
These shape how you structure work for agents:

5. **Standard Output** - Structured agent outputs for observability
6. **Types** - Data models and schemas that define interfaces
7. **Docs** - Documentation that provides context to agents
8. **Tests** - Validation that ensures agent work is correct
9. **Architecture** - System design that guides agent decisions
10. **Plans** - Specifications that break work into steps
11. **Templates** - Reusable prompt patterns (slash commands)
12. **AI Developer Workflows** - Orchestrated multi-agent processes

## Core Patterns

### Pattern 1: Subprocess-Based Execution

**When to use**: Simple prompts, shell compatibility, lower dependencies

```python
from agent import prompt_claude_code, AgentPromptRequest

request = AgentPromptRequest(
    prompt="Analyze this module",
    adw_id="abc12345",
    agent_name="analyzer",
    model="sonnet",
    output_file="agents/abc12345/analyzer/cc_raw_output.jsonl"
)

response = prompt_claude_code(request)
if response.success:
    print(response.output)
```

**Characteristics**:
- Invokes Claude Code CLI as subprocess
- Streams output to JSONL files
- Parses results into structured JSON
- Implements retry logic for transient failures
- Works with both subscription and API modes

### Pattern 2: SDK-Based Execution

**When to use**: Interactive sessions, better type safety, async workflows

```python
from agent_sdk import simple_query

response = await simple_query("Implement feature X")
print(response)
```

**Characteristics**:
- Native Python async/await
- Typed message objects
- SDK-specific error handling
- Interactive session support
- Better IDE integration

### Pattern 3: Template-Based Development

**Slash commands** are reusable prompt templates:

```markdown
# .claude/commands/chore.md
Create a plan using this format:

## Variables
adw_id: $1
description: $2

## Instructions
1. Analyze the codebase starting with README.md
2. Create a step-by-step plan
3. Save to specs/chore-{adw_id}-{name}.md
```

Execute: `./adws/adw_slash_command.py /chore abc123 "add logging"`

### Pattern 4: Workflow Orchestration

**Compound workflows** chain multiple agent invocations:

```python
# Phase 1: Planning
chore_response = execute_template(
    slash_command="/chore",
    args=[adw_id, description]
)

# Extract plan path from response
plan_path = extract_plan_path(chore_response.output)

# Phase 2: Implementation
implement_response = execute_template(
    slash_command="/implement",
    args=[plan_path]
)
```

## Observability First

Every ADW execution creates structured outputs:

```
agents/{adw_id}/{agent_name}/
  cc_raw_output.jsonl       # Raw streaming JSONL
  cc_raw_output.json         # Parsed JSON array
  cc_final_object.json       # Final result object
  custom_summary_output.json # High-level summary
```

**Why this matters**:
- Debug agent behavior by reading raw outputs
- Programmatically process results from JSON
- Track lineage with unique IDs
- Audit what agents did and why

## Progressive Enhancement

Start simple, add complexity as needed:

### Minimal (Always)
- Core subprocess execution (`agent.py`)
- Basic prompt wrapper (`adw_prompt.py`)
- Essential slash commands (chore, implement)
- Spec directory for plans

**Good for**: Proof of concepts, simple automation, getting started

### Enhanced (Recommended)
- SDK support (`agent_sdk.py`)
- Compound workflows (`adw_chore_implement.py`)
- Rich slash commands (feature, test, prime)
- Slash command executor

**Good for**: Active development, team collaboration, feature automation

### Scaled (Production)
- State management across phases
- Git worktree isolation
- Trigger systems (webhooks, cron)
- Testing infrastructure
- Comprehensive observability

**Good for**: Production systems, enterprise teams, complex SDLC

## Best Practices

### 1. Environment Safety
```python
# Filter environment variables
def get_safe_subprocess_env():
    return {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "HOME": os.getenv("HOME"),
        "PATH": os.getenv("PATH"),
        # Only essential variables
    }
```

**Why**: Prevents environment variable leakage, security isolation

### 2. Retry Logic
```python
def prompt_claude_code_with_retry(request, max_retries=3):
    for attempt in range(max_retries + 1):
        response = prompt_claude_code(request)
        if response.success or response.retry_code == RetryCode.NONE:
            return response
        time.sleep(retry_delays[attempt])
```

**Why**: Handle transient failures (network issues, rate limits, timeouts)

### 3. Error Truncation
```python
def truncate_output(output, max_length=500):
    if len(output) <= max_length:
        return output
    return output[:max_length-15] + "... (truncated)"
```

**Why**: Prevent console flooding from huge error messages

### 4. Unique ID Tracking
```python
def generate_short_id():
    return str(uuid.uuid4())[:8]

adw_id = generate_short_id()  # abc12345
# All outputs go to: agents/abc12345/
```

**Why**: Track execution lineage, associate outputs, debug flows

### 5. Type Safety
```python
from pydantic import BaseModel

class AgentPromptRequest(BaseModel):
    prompt: str
    adw_id: str
    model: Literal["sonnet", "opus"]
    output_file: str
```

**Why**: Catch errors early, better IDE support, self-documenting

## Usage Modes

### Mode A: Claude Max Subscription
- User has Claude Max subscription
- No API key needed
- Claude Code authenticates through subscription
- Perfect for interactive development

### Mode B: API-Based Automation
- Requires `ANTHROPIC_API_KEY`
- Enables headless automation
- Required for CI/CD, webhooks, cron jobs
- Programmatic agent execution

**Both modes work with the same ADW infrastructure.** The code detects which mode to use automatically.

## Philosophy: Scale Compute, Not Just Effort

Traditional development: **You write the code**
- Linear scaling: More features = more time
- Bottleneck: Your available hours
- Hard to parallelize

Agentic development: **You template patterns, agents write the code**
- Compute scaling: More features = more parallel agents
- Bottleneck: Compute availability
- Easy to parallelize

**This is the fundamental shift.** ADWs enable this paradigm.

## Key Insights

1. **Separation of Concerns**: Agentic layer (how to operate) vs Application layer (what to operate on)

2. **Progressive Enhancement**: Start minimal, add features as needed, scale when required

3. **Observability**: Structured outputs make agent behavior transparent and debuggable

4. **Intelligence Over Templating**: Provide patterns, let Claude adapt intelligently

5. **Mode Flexibility**: Support both interactive (subscription) and automated (API) workflows

6. **Compute as Leverage**: Scale impact by scaling compute, not just working harder

## Further Reading

- `architecture.md` - Detailed architecture patterns
- `usage-modes.md` - Deep dive on subscription vs API modes
- Reference implementations in `reference/` directory
- Main skill logic in `SKILL.md`
