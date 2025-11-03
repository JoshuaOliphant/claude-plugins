# ADW Architecture Deep Dive

## System Overview

ADW infrastructure creates a **programmatic interface** for AI-driven development by wrapping the application layer with an agentic layer that templates engineering patterns.

```
┌─────────────────────────────────────────────────────────────┐
│                     Agentic Layer                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ADW Scripts (adws/)                                  │  │
│  │  - Execute prompts programmatically                   │  │
│  │  - Orchestrate multi-phase workflows                  │  │
│  │  - Invoke Claude Code CLI or SDK                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Slash Commands (.claude/commands/)                   │  │
│  │  - Reusable prompt templates                          │  │
│  │  - Structured instructions for agents                 │  │
│  │  - Variable substitution                              │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Specifications (specs/)                              │  │
│  │  - Implementation plans                               │  │
│  │  - Step-by-step tasks                                 │  │
│  │  - Validation commands                                │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Claude Code (subprocess or SDK)                      │  │
│  │  - Executes prompts with tools                        │  │
│  │  - Modifies application code                          │  │
│  │  - Returns structured results                         │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Observability (agents/)                              │  │
│  │  - Structured outputs                                 │  │
│  │  - Execution tracking                                 │  │
│  │  - Debug artifacts                                    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│  - Your actual application code (apps/, src/, lib/)         │
│  - Tests, configs, documentation                            │
│  - What agents read and modify                              │
└─────────────────────────────────────────────────────────────┘
```

## Core Modules

### agent.py - Subprocess Execution Engine

**Purpose**: Core module for executing Claude Code CLI as subprocess

**Key Components**:

```python
# Data Models
class AgentPromptRequest(BaseModel):
    prompt: str              # What to execute
    adw_id: str             # Unique workflow ID
    agent_name: str         # Agent identifier
    model: Literal["sonnet", "opus"]
    output_file: str        # Where to save output
    working_dir: Optional[str]  # Where to run

class AgentPromptResponse(BaseModel):
    output: str             # Result text
    success: bool           # Did it succeed?
    session_id: Optional[str]  # Claude session ID
    retry_code: RetryCode   # Should we retry?

# Core Functions
def prompt_claude_code(request: AgentPromptRequest) -> AgentPromptResponse
def prompt_claude_code_with_retry(request: AgentPromptRequest) -> AgentPromptResponse
def execute_template(request: AgentTemplateRequest) -> AgentPromptResponse
```

**Execution Flow**:

1. **Build Command**
   ```python
   cmd = [
       "claude",
       "-p", prompt,
       "--model", model,
       "--output-format", "stream-json",
       "--verbose"
   ]
   ```

2. **Filter Environment**
   ```python
   env = get_safe_subprocess_env()
   # Only passes essential variables
   # Prevents environment leakage
   ```

3. **Execute & Stream**
   ```python
   subprocess.run(
       cmd,
       stdout=output_file,  # Stream to file
       stderr=subprocess.PIPE,
       env=env
   )
   ```

4. **Parse JSONL Output**
   ```python
   messages = [json.loads(line) for line in f]
   result_message = find_result_message(messages)
   ```

5. **Convert to Multiple Formats**
   - `cc_raw_output.jsonl` - Raw streaming JSONL
   - `cc_raw_output.json` - Parsed JSON array
   - `cc_final_object.json` - Final result object

6. **Return Response**
   ```python
   return AgentPromptResponse(
       output=result_text,
       success=not is_error,
       session_id=session_id,
       retry_code=RetryCode.NONE
   )
   ```

**Error Handling**:
- Retry codes distinguish transient from permanent errors
- Output truncation prevents console flooding
- Graceful degradation on parse failures

### agent_sdk.py - SDK Execution Engine

**Purpose**: Type-safe, async execution using Claude Code Python SDK

**Key Patterns**:

```python
# One-shot query
async def simple_query(prompt: str) -> str:
    options = ClaudeCodeOptions(model="claude-sonnet-4-20250514")
    texts = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            texts.append(extract_text(message))
    return "\n".join(texts)

# Interactive session
@asynccontextmanager
async def create_session():
    client = ClaudeSDKClient(options=options)
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()
```

**Advantages**:
- Native async/await patterns
- Typed message objects (AssistantMessage, ResultMessage)
- SDK-specific error handling
- Interactive session support
- Better IDE integration

**When to Use**:
- Interactive multi-turn conversations
- Need better type safety
- Async workflow integration
- Native Python integration preferred

## Data Flow Patterns

### Pattern 1: Direct Prompt Execution

```
User Input
    ↓
./adws/adw_prompt.py "analyze this"
    ↓
AgentPromptRequest created
    ↓
prompt_claude_code_with_retry()
    ↓
subprocess: claude -p "analyze this"
    ↓
JSONL output streamed to file
    ↓
Parse JSONL → JSON conversion
    ↓
AgentPromptResponse returned
    ↓
Display to user + save summary
```

### Pattern 2: Slash Command Execution

```
User Input
    ↓
./adws/adw_slash_command.py /chore abc123 "task"
    ↓
Read .claude/commands/chore.md
    ↓
Substitute variables ($1, $2)
    ↓
AgentTemplateRequest created
    ↓
execute_template() → prompt_claude_code_with_retry()
    ↓
subprocess: claude -p "<expanded template>"
    ↓
Parse results
    ↓
Extract spec path from output
    ↓
Display + save
```

### Pattern 3: Compound Workflow

```
User Input
    ↓
./adws/adw_chore_implement.py "feature X"
    ↓
Generate unique adw_id
    ↓
┌─────────────────────────────────────┐
│ Phase 1: Planning                   │
├─────────────────────────────────────┤
│ execute_template("/chore", args)    │
│     ↓                                │
│ Create plan in specs/               │
│     ↓                                │
│ Parse output for plan path          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Phase 2: Implementation             │
├─────────────────────────────────────┤
│ execute_template("/implement", path) │
│     ↓                                │
│ Read plan from specs/               │
│     ↓                                │
│ Execute step by step                │
│     ↓                                │
│ Modify application code             │
└─────────────────────────────────────┘
    ↓
Workflow summary saved
    ↓
Display results to user
```

## Directory Structure

### Minimal Setup

```
project/
├── adws/
│   ├── adw_modules/
│   │   └── agent.py              # Core execution
│   └── adw_prompt.py              # CLI wrapper
├── .claude/commands/
│   ├── chore.md                   # Planning template
│   └── implement.md               # Implementation template
├── specs/
│   └── *.md                       # Generated plans
├── agents/                        # Output directory
│   └── {adw_id}/
│       └── {agent_name}/
│           ├── cc_raw_output.jsonl
│           ├── cc_raw_output.json
│           ├── cc_final_object.json
│           └── custom_summary_output.json
└── .env.sample                    # Configuration template
```

### Enhanced Setup

```
project/
├── adws/
│   ├── adw_modules/
│   │   ├── agent.py               # Subprocess execution
│   │   └── agent_sdk.py           # SDK execution
│   ├── adw_prompt.py              # Direct prompts
│   ├── adw_slash_command.py       # Command executor
│   └── adw_chore_implement.py     # Compound workflow
├── .claude/commands/
│   ├── chore.md
│   ├── implement.md
│   ├── feature.md                 # Feature planning
│   ├── test.md                    # Test creation
│   ├── prime.md                   # Context loading
│   └── start.md                   # App startup
├── specs/
│   ├── chore-*.md
│   └── feature-*.md
├── agents/
│   └── {adw_id}/
│       ├── planner/               # Planning agent outputs
│       ├── builder/               # Building agent outputs
│       └── workflow_summary.json  # Overall summary
└── CLAUDE.md                      # Updated with ADW docs
```

### Scaled Setup (Production)

```
project/
├── adws/
│   ├── adw_modules/
│   │   ├── agent.py              # Subprocess execution
│   │   ├── agent_sdk.py          # SDK execution
│   │   ├── data_types.py         # Type definitions
│   │   ├── state.py              # State management (adw_state.json)
│   │   ├── git_ops.py            # Git operations (branch, commit, push, PR)
│   │   ├── worktree_ops.py       # Worktree isolation management
│   │   ├── workflow_ops.py       # High-level orchestration
│   │   ├── github.py             # GitHub integration (gh CLI)
│   │   └── utils.py              # Shared utilities
│   ├── adw_sdlc_iso.py           # Complete SDLC (plan→build→test→review→doc)
│   ├── adw_plan_build_test_review_iso.py  # Compound isolated workflow
│   ├── adw_ship_iso.py           # Merge validation and shipping
│   ├── adw_plan_iso.py           # Isolated planning phase
│   ├── adw_build_iso.py          # Isolated build phase
│   ├── adw_test_iso.py           # Isolated testing phase
│   ├── adw_review_iso.py         # Isolated review phase
│   └── adw_document_iso.py       # Isolated documentation phase
├── .claude/commands/
│   ├── chore.md
│   ├── bug.md
│   ├── feature.md
│   ├── implement.md
│   ├── classify_issue.md         # Issue classification
│   ├── classify_adw.md           # ADW workflow selection
│   ├── generate_branch_name.md   # Branch naming
│   ├── patch.md                  # Patch planning
│   ├── test.md                   # Test execution
│   ├── review.md                 # Code review
│   ├── document.md               # Documentation generation
│   ├── pull_request.md           # PR creation
│   ├── install_worktree.md       # Worktree environment setup
│   ├── cleanup_worktrees.md      # Worktree cleanup
│   ├── commit.md                 # Commit message generation
│   ├── prime.md
│   └── start.md
├── specs/
│   ├── chore-*.md
│   ├── bug-*.md
│   ├── feature-*.md
│   └── patch/                    # Patch plans
├── agents/
│   └── {adw_id}/
│       ├── {agent_name}/         # Per-agent outputs
│       ├── adw_state.json        # Persistent state
│       └── workflow_summary.json
├── trees/                        # Git worktree isolation
│   └── {adw_id}/                 # Isolated working directory
│       ├── .ports.env            # Port configuration
│       └── <full repo copy>
├── .adw_backups/                 # Safety backups during upgrades
├── CLAUDE.md                     # Updated with ADW docs
└── .env.sample                   # Configuration
```

**Key Scaled Phase Features:**

1. **State Management**: Persistent state across workflow phases via `adw_state.json`
2. **Git Worktree Isolation**: Each ADW runs in isolated `trees/{adw_id}/` directory
3. **Port Management**: Deterministic port allocation (9100-9114 backend, 9200-9214 frontend)
4. **GitHub Integration**: Issue operations, PR management, comment posting via gh CLI
5. **Multi-Phase Workflows**: Complete SDLC automation (plan, build, test, review, document, ship)
6. **Workflow Composition**: High-level functions for issue classification, branch generation, etc.
7. **Advanced Commands**: Rich library of 20+ specialized slash commands

## Output Structure

### Observability Artifacts

Each ADW execution creates:

**cc_raw_output.jsonl**
- Line-delimited JSON
- Streaming output from Claude Code
- Each line is a message object
- Last line is result message

**cc_raw_output.json**
- JSON array of all messages
- Easier for programmatic processing
- Contains full conversation history

**cc_final_object.json**
- Just the last message (result)
- Quick access to final output
- Contains success/failure info

**custom_summary_output.json**
- High-level execution summary
- Metadata (adw_id, prompt, model)
- Success status
- Session ID for debugging

### Workflow Tracking

For compound workflows:

**workflow_summary.json**
```json
{
  "workflow": "chore_implement",
  "adw_id": "abc12345",
  "prompt": "add error handling",
  "phases": {
    "planning": {
      "success": true,
      "session_id": "session_xyz",
      "agent": "planner",
      "output_dir": "agents/abc12345/planner/"
    },
    "implementation": {
      "success": true,
      "session_id": "session_abc",
      "agent": "builder",
      "output_dir": "agents/abc12345/builder/"
    }
  },
  "overall_success": true
}
```

## Retry Logic Architecture

### Retry Code Classification

```python
class RetryCode(str, Enum):
    CLAUDE_CODE_ERROR = "claude_code_error"      # Retry
    TIMEOUT_ERROR = "timeout_error"              # Retry
    EXECUTION_ERROR = "execution_error"          # Retry
    ERROR_DURING_EXECUTION = "error_during_execution"  # Retry
    NONE = "none"                                # Don't retry
```

### Retry Decision Flow

```
Execute prompt
    ↓
Success? → Return response
    ↓ No
Check retry_code
    ↓
NONE? → Return response (don't retry)
    ↓ No
Retryable error?
    ↓ Yes
Attempts < max_retries?
    ↓ Yes
Wait (exponential backoff: 1s, 3s, 5s)
    ↓
Retry execution
    ↓
(Loop back to top)
    ↓
Max retries reached? → Return last response
```

### Default Configuration

```python
max_retries = 3
retry_delays = [1, 3, 5]  # seconds

# Exponential backoff:
# Attempt 1: fail → wait 1s
# Attempt 2: fail → wait 3s
# Attempt 3: fail → wait 5s
# Attempt 4: return failure
```

## Environment Safety

### Security Model

```python
def get_safe_subprocess_env() -> Dict[str, str]:
    """Only pass essential environment variables."""
    safe_vars = {
        # Authentication
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),

        # System essentials
        "HOME": os.getenv("HOME"),
        "USER": os.getenv("USER"),
        "PATH": os.getenv("PATH"),
        "SHELL": os.getenv("SHELL"),

        # Python-specific
        "PYTHONPATH": os.getenv("PYTHONPATH"),
        "PYTHONUNBUFFERED": "1",

        # Working directory
        "PWD": os.getcwd(),
    }

    # Filter out None values
    return {k: v for k, v in safe_vars.items() if v is not None}
```

**Why this matters**:
- Prevents leaking sensitive variables
- Subprocess isolation
- Explicit allowlist vs implicit inheritance
- Security boundary between layers

## Subprocess vs SDK: Decision Matrix

| Criteria | Subprocess (agent.py) | SDK (agent_sdk.py) |
|----------|----------------------|-------------------|
| **Type Safety** | Basic (dicts) | Strong (typed objects) |
| **Error Handling** | Generic exceptions | SDK-specific exceptions |
| **Async Support** | Subprocess management | Native async/await |
| **Dependencies** | Minimal (subprocess, json) | claude-code-sdk package |
| **Debugging** | Read JSONL files | SDK message inspection |
| **Interactive Sessions** | ❌ Not supported | ✅ ClaudeSDKClient |
| **Shell Compatibility** | ✅ Works everywhere | Python only |
| **Use Case** | Simple prompts, automation | Complex workflows, sessions |
| **Learning Curve** | Low (familiar subprocess) | Medium (SDK concepts) |
| **Performance** | Process spawn overhead | Native Python speed |

## Scalability Patterns

### Horizontal Scaling

Run multiple ADWs in parallel:

```bash
# Terminal 1
./adws/adw_chore_implement.py "feature A" &

# Terminal 2
./adws/adw_chore_implement.py "feature B" &

# Terminal 3
./adws/adw_chore_implement.py "feature C" &

# Each gets unique adw_id
# Outputs don't conflict
# Scale compute → scale features
```

### Vertical Scaling

Break complex tasks into phases:

```
Large Feature
    ↓
Phase 1: Architecture Design
    ↓
Phase 2: Core Implementation
    ↓
Phase 3: Testing
    ↓
Phase 4: Documentation
    ↓
Phase 5: Deployment
```

Each phase is separate ADW execution with clear handoffs.

## Key Design Decisions

### 1. JSONL as Interchange Format
- Streamable (process as it arrives)
- Line-delimited (easy to parse)
- Standard format (widely supported)

### 2. Unique ID per Execution
- Enables parallel execution
- Clear output isolation
- Audit trail maintenance
- Debugging support

### 3. Multiple Output Formats
- JSONL for streaming
- JSON for processing
- Final object for quick access
- Summary for humans

### 4. Subprocess First, SDK Optional
- Lower barrier to entry
- Subprocess is universal
- SDK adds sophistication later
- Progressive enhancement

### 5. Environment Filtering
- Security boundary
- Explicit allowlist
- Prevents accidents
- Isolation guarantee

## Extension Points

Where to extend the architecture:

1. **New ADW Scripts** (`adws/adw_*.py`)
   - Add new orchestration patterns
   - Implement domain-specific workflows

2. **New Slash Commands** (`.claude/commands/*.md`)
   - Template new engineering patterns
   - Capture team conventions

3. **New Agent Modules** (`adws/adw_modules/*.py`)
   - Add state management
   - Implement workflow helpers
   - Add integrations

4. **Hooks** (`.claude/hooks/*.py`)
   - Pre/post tool use events
   - Notification systems
   - Validation gates

5. **Triggers** (`adws/adw_triggers/*.py`)
   - Webhook endpoints
   - Cron jobs
   - Event handlers

6. **Custom Subagents** (`.claude/agents/*.md`)
   - Specialized agent configurations
   - Domain experts
   - Tool restrictions

## Performance Considerations

### Bottlenecks

1. **Claude Code Execution Time**
   - Dominant factor
   - Minutes per complex task
   - Mitigate: Run in parallel

2. **Subprocess Spawn Overhead**
   - Minimal (~100ms)
   - Negligible compared to execution
   - SDK slightly faster but not significant

3. **JSONL Parsing**
   - Fast (JSON is efficient)
   - Linear in message count
   - Not a bottleneck in practice

### Optimization Strategies

1. **Parallel Execution**
   - Run independent tasks concurrently
   - Each gets own adw_id
   - No shared state conflicts

2. **Appropriate Model Selection**
   - Use Sonnet for most tasks (faster, cheaper)
   - Use Opus only for complex reasoning
   - 2-3x speed difference

3. **Caching**
   - Claude Code has built-in caching
   - Repeated prompts are faster
   - Design for cache reuse

4. **Progressive Enhancement**
   - Start minimal (faster setup)
   - Add features as needed
   - Don't over-engineer initially
