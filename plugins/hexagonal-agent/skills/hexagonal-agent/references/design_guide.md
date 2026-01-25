# Hexagonal Agent Application Design Guide

A framework for designing applications where an AI agent generates UI dynamically based on user intent. Uses the Anthropic Agent SDK as the prompt object implementation.

---

## The Three Design Decisions

Building a hexagonal agent application requires three interconnected design decisions:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   1. TOOLS                    2. SKILL FILE                     │
│   What can the agent do?      How does it express itself?       │
│                                                                 │
│   • Domain capabilities       • Visual vocabulary               │
│   • Data operations           • Interaction patterns            │
│   • External integrations     • Component conventions           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   3. HTTP ADAPTER                                               │
│   How do users interact?                                        │
│                                                                 │
│   • Input mechanisms (chat, forms, voice, etc.)                 │
│   • Output targets (where HTML gets rendered)                   │
│   • Session management (per-user, shared, ephemeral)            │
│   • Navigation structure (single page, multi-page, modal)       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

These three decisions are **interdependent**. Tools constrain what the skill file can teach. The skill file shapes what UI patterns are possible. The HTTP adapter determines how those patterns reach users.

---

## 1. Designing Tools

Tools define the agent's **capability boundary**—what it can perceive and affect in the world.

### Questions to Answer

**What data does the agent need to read?**
- User data (profiles, preferences, history)
- Domain data (products, content, records)
- External data (APIs, services, real-time feeds)

**What actions can the agent take?**
- Create, update, delete operations
- Workflow triggers
- External service calls
- Notifications or communications

**What's the appropriate granularity?**
- Too coarse: Agent can't compose behaviors
- Too fine: Agent wastes tokens on minutiae
- Right level: Atomic operations that combine naturally

### Tool Design Principles

**1. Tools should be atomic and composable**

```python
# Good: Atomic operations the agent can combine
list_tasks()
add_task(title, priority)
complete_task(task_id)
get_tasks_by_status(status)

# Bad: Monolithic operations that assume workflows
manage_task_lifecycle(action, task_id, new_status, ...)
```

**2. Tools should return data, not UI**

```python
# Good: Returns structured data
@tool("get_order", "Retrieve order details", {"order_id": str})
async def get_order(args):
    order = db.get_order(args["order_id"])
    return {"content": [{"type": "text", "text": json.dumps({
        "id": order.id,
        "status": order.status,
        "items": order.items,
        "total": order.total
    })}]}

# Bad: Returns pre-formatted output
@tool("get_order", "Retrieve order details", {"order_id": str})
async def get_order(args):
    order = db.get_order(args["order_id"])
    return {"content": [{"type": "text", "text": f"Order #{order.id}: {order.status}"}]}
```

The agent decides how to present data. Tools just provide it.

**3. Tool names and descriptions matter**

The agent uses descriptions to decide when to call tools. Be precise:

```python
# Good: Clear about what it does and when to use it
@tool(
    "search_products",
    "Search product catalog by keyword. Use when user wants to find or browse products. Returns up to 20 matching products with name, price, and availability.",
    {"query": str, "category": str, "max_results": int}
)

# Bad: Vague, agent won't know when to use it
@tool("search", "Search for things", {"q": str})
```

**4. Consider the failure modes**

```python
@tool("get_user_profile", "Get current user's profile", {})
async def get_user_profile(args):
    user = get_current_user()
    if not user:
        return {
            "content": [{"type": "text", "text": json.dumps({
                "error": "not_authenticated",
                "message": "User must be logged in"
            })}],
            "is_error": True
        }
    return {"content": [{"type": "text", "text": json.dumps(user.to_dict())}]}
```

### Tool Categories by Application Type

| Application Type | Read Tools | Write Tools | Integration Tools |
|-----------------|------------|-------------|-------------------|
| Task Manager | list_tasks, get_task, search_tasks | add_task, update_task, complete_task, delete_task | sync_calendar, send_reminder |
| E-commerce | list_products, get_product, get_cart, get_order | add_to_cart, remove_from_cart, place_order | check_inventory, calculate_shipping |
| Support Desk | list_tickets, get_ticket, search_knowledge_base | create_ticket, update_ticket, add_note | send_email, escalate_ticket |
| Content CMS | list_posts, get_post, list_categories | create_post, update_post, publish_post | upload_media, schedule_post |
| Analytics | get_metrics, get_report, compare_periods | create_alert, save_report | export_data, refresh_data |

---

## 2. Designing the Skill File

The skill file teaches the agent **how to express itself**—the visual vocabulary, interaction patterns, and domain conventions.

### Questions to Answer

**What CSS framework/design system?**
- Tailwind (utility-first, flexible)
- DaisyUI (component classes, opinionated)
- Custom CSS (full control, more to teach)
- Framework components (shadcn, etc.)

**What's the visual tone?**
- Professional/enterprise
- Playful/consumer
- Minimal/focused
- Data-dense/dashboard

**What interaction patterns exist?**
- How are lists displayed?
- How are forms structured?
- How is feedback shown?
- How do actions trigger?

**What's the HTMX integration model?**
- What targets exist?
- What swap strategies?
- How do loading states work?

### Skill File Structure

```markdown
# {Domain} UI Skill

[Role and responsibility statement]

## Design System

### Visual Foundation
[Colors, typography, spacing conventions]

### Component Patterns
[Cards, lists, tables, forms, alerts—with full HTML examples]

### HTMX Integration
[Targets, triggers, swap patterns, loading states]

## Available Tools

[List each tool with when to use it]

## Interaction Patterns

### Pattern: [Name]
When: [Trigger condition]
Action: [What agent should do]
Example: [HTML output]

[Repeat for each pattern]

## Output Rules

[Strict formatting requirements]
```

### Skill File Design Principles

**1. Show, don't just tell**

```markdown
# Bad: Abstract instruction
Use cards for content sections.

# Good: Concrete example
### Cards
Wrap distinct content in cards:
```html
<div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
  <h3 class="text-lg font-semibold text-white mb-2">Card Title</h3>
  <p class="text-slate-300">Card content goes here.</p>
</div>
```
```

**2. Define interaction patterns explicitly**

```markdown
## Interaction Patterns

### Pattern: Show Collection
When: User asks to see/list/show multiple items
Action: Call the appropriate list tool, render as cards or table
Example:
```html
<div class="space-y-3">
  <div class="flex justify-between items-center">
    <h2 class="text-xl font-bold">Your Tasks</h2>
    <button hx-post="/agent" hx-vals='{"message":"add a task"}'
            hx-target="#content" class="btn-primary">+ Add</button>
  </div>
  <div class="space-y-2">
    <!-- Task cards here -->
  </div>
</div>
```

### Pattern: Create Item (Info Missing)
When: User wants to create something but hasn't provided required details
Action: Generate a form to collect the information
Example:
```html
<form hx-post="/agent" hx-target="#content" class="card">
  <h3>New Task</h3>
  <input type="text" name="title" placeholder="Task title" required>
  <input type="hidden" name="message" value="create task with title from form">
  <button type="submit">Create</button>
</form>
```

### Pattern: Create Item (Info Complete)
When: User provides all required information inline
Action: Call the create tool, show success confirmation
Example: User says "add task: review PR" → call add_task, show:
```html
<div class="alert-success">
  <p>✓ Created task: "review PR"</p>
  <button hx-post="/agent" hx-vals='{"message":"show my tasks"}'
          hx-target="#content">View All Tasks</button>
</div>
```
```

**3. Match complexity to domain**

A data-heavy dashboard needs different patterns than a simple todo app:

```markdown
# Simple App Skill (e.g., Task Manager)
- Cards for items
- Simple forms
- Inline actions

# Complex App Skill (e.g., Analytics Dashboard)
- Grid layouts for multiple data views
- Tabs for different perspectives
- Charts and visualizations
- Filter controls
- Drill-down patterns
```

**4. Define the boundaries**

```markdown
## Output Rules

1. Output ONLY raw HTML—no markdown, no code fences
2. Always include HTMX attributes for interactive elements
3. Never generate JavaScript inline (rely on HTMX)
4. Maximum response: one logical "screen" of content
5. For long lists, paginate or summarize
```

### Skill File Examples by Domain

**Minimal (Chat Assistant)**

```markdown
# Chat UI Skill
Respond conversationally in a single card. Keep responses concise.

### Response Card
```html
<div class="bg-slate-800 rounded-lg p-4 max-w-2xl">
  <p class="text-slate-200">[Your response here]</p>
</div>
```
```

**Data-Centric (Admin Dashboard)**

```markdown
# Admin Dashboard Skill
Display data in tables with sort/filter controls. Use stats cards for KPIs.
Support drill-down via hx-get on table rows.

### Stats Row
```html
<div class="grid grid-cols-4 gap-4">
  <div class="stat-card">
    <p class="stat-label">Total Users</p>
    <p class="stat-value">1,234</p>
    <p class="stat-change positive">+12%</p>
  </div>
  <!-- more stats -->
</div>
```

### Data Table
```html
<div class="overflow-x-auto">
  <table class="data-table">
    <thead>...</thead>
    <tbody>
      <tr hx-get="/agent?message=show+user+123" hx-target="#detail-panel">
        <!-- Clickable row for drill-down -->
      </tr>
    </tbody>
  </table>
</div>
```
```

**Workflow-Oriented (Support Ticket System)**

```markdown
# Support Ticket Skill
Show ticket status prominently. Actions depend on current status.
Always show customer context alongside ticket details.

### Ticket Detail
```html
<div class="grid grid-cols-3 gap-4">
  <div class="col-span-2">
    <!-- Ticket content, history -->
  </div>
  <div>
    <!-- Customer sidebar, actions based on status -->
  </div>
</div>
```
```

---

## 3. Designing the HTTP Adapter

The HTTP adapter determines **how users interact** with the agent—input mechanisms, output targets, session handling, and navigation.

### Questions to Answer

**How do users provide input?**
- Text chat (most common)
- Voice input
- Structured forms
- File uploads
- URL parameters / deep links

**Where does output render?**
- Single content area (simple)
- Multiple target zones (dashboard)
- Modal/overlay system
- Full page replacement

**How is session state managed?**
- Per-user persistent sessions
- Ephemeral (reset each visit)
- Shared/collaborative sessions
- Anonymous vs authenticated

**What's the navigation model?**
- Single-page with HTMX swaps
- Multi-page with shared agent context
- Wizard/step-based flows
- Tab-based views

### HTTP Adapter Patterns

**Pattern: Simple Chat Interface**

Single input, single output area. Most straightforward.

```python
@app.post("/agent")
async def handle_message(message: str = Form(...)):
    return await agent.process(message)
```

```html
<div id="content"><!-- Agent output here --></div>
<form hx-post="/agent" hx-target="#content">
    <input type="text" name="message">
    <button type="submit">Send</button>
</form>
```

**Pattern: Multi-Zone Dashboard**

Different areas of the page can be updated independently.

```python
@app.post("/agent/main")
async def handle_main(message: str = Form(...)):
    return await agent.process(message, zone="main")

@app.post("/agent/sidebar")
async def handle_sidebar(message: str = Form(...)):
    return await agent.process(message, zone="sidebar")
```

```html
<div class="grid grid-cols-4">
    <div id="sidebar" class="col-span-1"><!-- Sidebar content --></div>
    <div id="main" class="col-span-3"><!-- Main content --></div>
</div>
<form hx-post="/agent/main" hx-target="#main">...</form>
```

**Pattern: Modal Overlays**

Actions open modals; confirmations close them.

```html
<div id="content"><!-- Main content --></div>
<div id="modal" class="modal hidden"><!-- Modal content --></div>

<!-- Trigger modal -->
<button hx-post="/agent" hx-target="#modal"
        hx-vals='{"message":"show add task form"}'
        onclick="document.getElementById('modal').classList.remove('hidden')">
    Add Task
</button>
```

**Pattern: Wizard/Multi-Step**

Agent guides through a process, maintaining step state.

```python
@app.post("/agent")
async def handle_message(
    message: str = Form(...),
    step: str = Form(default="start")
):
    return await agent.process(message, context={"current_step": step})
```

```html
<!-- Agent includes hidden step field in forms -->
<form hx-post="/agent" hx-target="#content">
    <input type="hidden" name="step" value="2">
    <input type="text" name="message">
    <button type="submit">Next</button>
</form>
```

**Pattern: Per-User Sessions**

Each user gets their own conversation context.

```python
from fastapi import Depends

agents: dict[str, Agent] = {}

async def get_agent(user_id: str = Depends(get_current_user_id)) -> Agent:
    if user_id not in agents:
        agents[user_id] = Agent()
    return agents[user_id]

@app.post("/agent")
async def handle_message(
    message: str = Form(...),
    agent: Agent = Depends(get_agent)
):
    return await agent.process(message)
```

### Adapter Design Considerations

**Loading States**

HTMX provides `htmx-request` class during requests:

```html
<style>
    .htmx-request .loading { display: block; }
    .htmx-request .content { opacity: 0.5; }
    .loading { display: none; }
</style>

<div id="content">
    <div class="loading">Processing...</div>
    <div class="content"><!-- Actual content --></div>
</div>
```

**Error Handling**

```python
@app.post("/agent")
async def handle_message(message: str = Form(...)):
    try:
        return await agent.process(message)
    except RateLimitError:
        return error_html("Too many requests. Please wait.")
    except Exception as e:
        logger.exception("Agent error")
        return error_html("Something went wrong. Please try again.")
```

**Request Timeout**

```python
import asyncio

@app.post("/agent")
async def handle_message(message: str = Form(...)):
    try:
        return await asyncio.wait_for(
            agent.process(message),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        return error_html("Request timed out. Please try a simpler query.")
```

**CORS for Embedded Use**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-parent-site.com"],
    allow_methods=["POST"],
)
```

---

## Design Process

### Step 1: Define the Domain

- What problem does this application solve?
- Who are the users?
- What are the core workflows?

### Step 2: Map Capabilities to Tools

- What data exists? → Read tools
- What actions are possible? → Write tools
- What external systems? → Integration tools
- What's the right granularity?

### Step 3: Design the Visual Language

- What framework/system?
- What components are needed?
- What interaction patterns?
- How does HTMX integrate?

### Step 4: Define the Interaction Model

- How do users input?
- Where does output go?
- How is state managed?
- What's the navigation?

### Step 5: Write the Skill File

- Document the design system
- Define interaction patterns with examples
- List tools and their purposes
- Set output rules

### Step 6: Implement

- Define tools with `@tool` decorator
- Create MCP server
- Build FastAPI adapter
- Test the full loop

---

## Checklist

### Tools

- [ ] All necessary read operations defined
- [ ] All necessary write operations defined
- [ ] Tools return structured data, not formatted strings
- [ ] Tool descriptions are clear and specific
- [ ] Error cases handled gracefully
- [ ] Appropriate granularity (atomic, composable)

### Skill File

- [ ] Design system documented with examples
- [ ] All component patterns shown as HTML
- [ ] HTMX attributes specified
- [ ] Interaction patterns defined (show, create, update, delete)
- [ ] Form patterns for data collection
- [ ] Feedback patterns (success, error, loading)
- [ ] Output rules clearly stated

### HTTP Adapter

- [ ] Input mechanism appropriate for use case
- [ ] Output targets defined
- [ ] Session management implemented
- [ ] Loading states handled
- [ ] Errors handled gracefully
- [ ] Timeouts configured
- [ ] Security considerations addressed

---

## Infrastructure (Reference)

The SDK handles the agent mechanics. For reference, the minimal implementation:

```python
# tools.py
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("tool_name", "description", {"param": str})
async def tool_name(args):
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

tools_server = create_sdk_mcp_server("app", tools=[tool_name, ...])
```

```python
# agent.py
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

class Agent:
    async def process(self, message: str) -> str:
        await self.client.query(message)
        html = ""
        async for msg in self.client.receive_response():
            # extract text blocks
        return html
```

```python
# main.py
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

@app.post("/agent")
async def handle(message: str = Form(...)):
    return await agent.process(message)
```

The design decisions—tools, skill file, adapter—are where the real work happens.
