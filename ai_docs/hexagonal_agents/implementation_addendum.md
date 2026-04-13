# Implementation Guide Addendum

This addendum addresses gaps identified during testing. Integrate these sections into the main Implementation Guide.

---

## SDK Installation

### Prerequisites

```bash
# Python 3.11+
pip install claude-agent-sdk fastapi uvicorn python-multipart

# Or with uv
uv add claude-agent-sdk fastapi uvicorn python-multipart
```

**Current version:** 0.1.22 (as of January 2025)

The `claude-agent-sdk` package provides:
- `ClaudeSDKClient` - The prompt object that manages conversation state
- `@tool` decorator - For defining MCP tools
- `create_sdk_mcp_server()` - Creates an MCP server from decorated functions
- Message types for inspecting responses

### Verify Installation

```python
from claude_agent_sdk import ClaudeSDKClient, tool, create_sdk_mcp_server
print("SDK installed successfully")
```

---

## Parameter Schema Reference

The `@tool` decorator's schema parameter uses a simplified type annotation format:

### Basic Types

```python
@tool("my_tool", "Description", {
    "name": str,           # Required string
    "count": int,          # Required integer
    "price": float,        # Required float
    "active": bool,        # Required boolean
})
```

### Optional Parameters

Use `| None` syntax for optional parameters:

```python
@tool("create_item", "Create with optional description", {
    "title": str,                    # Required
    "description": str | None,       # Optional (can be None)
    "priority": str | None,          # Optional
})
def create_item(title: str, description: str | None = None, priority: str | None = None):
    # Handle None values
    desc = description or "No description"
    prio = priority or "medium"
    ...
```

### Default Values

Defaults are specified in the function signature, not the schema:

```python
@tool("search", "Search with pagination", {
    "query": str,
    "limit": int | None,
    "offset": int | None,
})
def search(query: str, limit: int = 10, offset: int = 0):
    # limit defaults to 10, offset to 0
    ...
```

### Complex Types

For lists and nested objects, use Python type hints:

```python
from typing import List, Dict, Any

@tool("bulk_create", "Create multiple items", {
    "items": list,  # Schema shows it's a list
})
def bulk_create(items: List[Dict[str, Any]]):
    # items is a list of dictionaries
    for item in items:
        title = item.get("title")
        ...
```

**Note:** The LLM receives the schema as guidance. Complex nested schemas work best when the tool description clearly explains the expected structure:

```python
@tool(
    "bulk_create",
    "Create multiple items. Each item should have: title (required), description (optional), priority (optional: low/medium/high)",
    {"items": list}
)
```

---

## MCP Server Name Matching

### The Naming Pattern

Tool names in `allowed_tools` follow this exact pattern:
```
mcp__{server_name}__{tool_name}
```

**Both underscores are double underscores (`__`).**

### Matching Requirements

The `server_name` must exactly match the key in `mcp_servers={}`:

```python
# Server created with name "app"
mcp_server = create_sdk_mcp_server(list_items, create_item, ...)

# Client must use "app" as the key
client = ClaudeSDKClient(
    model="claude-sonnet-4-20250514",
    system=SKILL_CONTENT,
    mcp_servers={"app": mcp_server},  # ← "app" is the server name
    allowed_tools=[
        "mcp__app__list_items",   # ← Must match: mcp__{app}__{tool}
        "mcp__app__create_item",
    ],
)
```

### Debugging Name Mismatches

If tools aren't being called:

1. **Print registered tools:**
```python
mcp_server = create_sdk_mcp_server(list_items, create_item)
print("Registered tools:", list(mcp_server.tools.keys()))
```

2. **Check allowed_tools list:**
```python
allowed = ["mcp__app__list_items", "mcp__app__create_item"]
for tool_name in allowed:
    parts = tool_name.split("__")
    print(f"Server: {parts[1]}, Tool: {parts[2]}")
```

3. **Verify server key matches:**
```python
server_key = "app"  # Must match the key in mcp_servers={}
for tool in mcp_server.tools.keys():
    print(f"Full name: mcp__{server_key}__{tool}")
```

---

## Form Data Flow (Detailed)

### 1. HTML Form Submission

```html
<form hx-post="/agent" hx-target="#content">
  <input type="text" name="title" value="The Hobbit">
  <input type="text" name="author" value="J.R.R. Tolkien">
  <input type="hidden" name="message" value="add this book">
  <button type="submit">Add Book</button>
</form>
```

### 2. FastAPI Receives Form Data

```python
@app.post("/agent")
async def agent_endpoint(request: Request):
    form = await request.form()
    
    # Extract the base message
    message = form.get("message", "")
    
    # Collect extra fields (everything except 'message')
    extra_fields = {k: v for k, v in form.items() if k != "message"}
    
    # Result: message="add this book", extra_fields={"title": "The Hobbit", "author": "J.R.R. Tolkien"}
```

### 3. Append Fields to Message

```python
    # Append fields in a parseable format
    if extra_fields:
        field_str = ", ".join(f"{k}={v}" for k, v in extra_fields.items())
        full_message = f"{message} [{field_str}]"
    else:
        full_message = message
    
    # Result: "add this book [title=The Hobbit, author=J.R.R. Tolkien]"
```

### 4. Agent Receives Combined Message

The agent sees:
```
add this book [title=The Hobbit, author=J.R.R. Tolkien]
```

### 5. Skill File Teaches Parsing

In your skill file, include guidance:

```markdown
## Form Data

When users submit forms, you'll receive messages like:
"action description [field1=value1, field2=value2]"

Extract the values and use them with the appropriate tool.

Example:
- Message: "add this book [title=The Hobbit, author=J.R.R. Tolkien]"
- Action: Call add_book with title="The Hobbit", author="J.R.R. Tolkien"
```

### Alternative: Structured Form Data

For complex forms, you can use JSON in a hidden field:

```html
<form hx-post="/agent" hx-target="#content">
  <input type="hidden" name="message" value="create book">
  <input type="hidden" name="data" id="form-data">
  <input type="text" id="title" placeholder="Title">
  <input type="text" id="author" placeholder="Author">
  <button type="submit" onclick="document.getElementById('form-data').value = JSON.stringify({title: document.getElementById('title').value, author: document.getElementById('author').value})">
    Add
  </button>
</form>
```

Then in the endpoint:
```python
data_str = form.get("data", "{}")
data = json.loads(data_str)
full_message = f"{message} with data: {json.dumps(data)}"
```

---

## Message Type Reference

### Response Iteration

```python
response = await client.receive_response()

# response.content is the final text/HTML output
html = response.content

# response.messages contains the full conversation
for msg in response.messages:
    if hasattr(msg, 'role'):
        print(f"Role: {msg.role}")
    
    # Check message type
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                print(f"Text: {block.text}")
            elif isinstance(block, ToolUseBlock):
                print(f"Tool: {block.name}, Input: {block.input}")
    
    elif isinstance(msg, ResultMessage):
        print(f"Tool result: {msg.content}")
```

### Common Message Types

| Type | Description | Key Attributes |
|------|-------------|----------------|
| `UserMessage` | User input | `content` (str) |
| `AssistantMessage` | Model response | `content` (list of blocks) |
| `TextBlock` | Text content | `text` (str) |
| `ToolUseBlock` | Tool invocation | `name`, `input`, `id` |
| `ResultMessage` | Tool result | `content`, `tool_use_id` |

### Accessing Tool Calls

```python
def get_tool_calls(response) -> list[dict]:
    """Extract all tool calls from a response."""
    calls = []
    for msg in response.messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, ToolUseBlock):
                    calls.append({
                        "name": block.name,
                        "input": block.input,
                        "id": block.id,
                    })
    return calls
```

---

## Cross-Reference Guide

### Design Guide → Implementation Guide

| Design Guide Section | Implementation Guide Section |
|---------------------|------------------------------|
| "Tool Design Principles" | "Step 2: Define MCP Tools" |
| "Skill File Structure" | "Step 3: Create the Skill File" |
| "HTTP Adapter Patterns" | "Step 4: Build the HTTP Adapter" |
| "Design Questions: Tools" | Parameter Schema Reference (this addendum) |

### Implementation Guide → Design Guide

| Implementation Guide Section | Design Guide Section |
|------------------------------|---------------------|
| "What tools does your app need?" | "Part 1: Tool Design" |
| "What UI patterns will the agent use?" | "Part 2: Skill File Design" |
| "Debugging: Agent not calling tools" | "Tool Design Principles" (check descriptions) |

### Implementation Guide → Eval Guide

| Implementation Guide Section | Eval Guide Section |
|------------------------------|-------------------|
| "Step 2: Define MCP Tools" | "Tool Usage Evaluators" |
| "Step 5: Run and Test" | "Step 1: Create the Task Function" |
| "Debugging" | "Eval Development Workflow" |

### Implementation Guide → UI Design Skill

| Implementation Guide Section | UI Design Skill Section |
|------------------------------|------------------------|
| "Step 3: Create the Skill File" | Entire document (use as skill content) |
| "Common HTML patterns" | "Component Patterns" |

---

## Additional UI Patterns

### Star Rating Input

```html
<div class="flex items-center gap-1">
  <span class="text-sm text-slate-400 mr-2">Rating:</span>
  
  <!-- Radio buttons styled as stars -->
  <input type="radio" name="rating" value="1" id="star1" class="hidden peer/star1">
  <label for="star1" class="cursor-pointer text-2xl text-slate-600 hover:text-amber-400 peer-checked/star1:text-amber-400">★</label>
  
  <input type="radio" name="rating" value="2" id="star2" class="hidden peer/star2">
  <label for="star2" class="cursor-pointer text-2xl text-slate-600 hover:text-amber-400 peer-checked/star2:text-amber-400">★</label>
  
  <input type="radio" name="rating" value="3" id="star3" class="hidden peer/star3">
  <label for="star3" class="cursor-pointer text-2xl text-slate-600 hover:text-amber-400 peer-checked/star3:text-amber-400">★</label>
  
  <input type="radio" name="rating" value="4" id="star4" class="hidden peer/star4">
  <label for="star4" class="cursor-pointer text-2xl text-slate-600 hover:text-amber-400 peer-checked/star4:text-amber-400">★</label>
  
  <input type="radio" name="rating" value="5" id="star5" class="hidden peer/star5">
  <label for="star5" class="cursor-pointer text-2xl text-slate-600 hover:text-amber-400 peer-checked/star5:text-amber-400">★</label>
</div>
```

### Star Rating Display (Read-only)

```html
<div class="flex items-center gap-0.5">
  <!-- 4 out of 5 stars -->
  <span class="text-amber-400">★★★★</span>
  <span class="text-slate-600">★</span>
</div>
```

### Status Badges (Domain-Specific)

```html
<!-- Want to Read -->
<span class="px-2.5 py-1 text-xs font-medium rounded-full bg-blue-500/20 text-blue-300">
  Want to Read
</span>

<!-- Currently Reading -->
<span class="px-2.5 py-1 text-xs font-medium rounded-full bg-amber-500/20 text-amber-300">
  Reading
</span>

<!-- Finished -->
<span class="px-2.5 py-1 text-xs font-medium rounded-full bg-emerald-500/20 text-emerald-300">
  Finished
</span>

<!-- Generic/Inactive -->
<span class="px-2.5 py-1 text-xs font-medium rounded-full bg-slate-700 text-slate-400">
  Archived
</span>
```

### Notes List

```html
<div class="space-y-3">
  <h4 class="text-sm font-medium text-slate-300">Notes</h4>
  
  <!-- Note item -->
  <div class="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
    <p class="text-slate-300 text-sm">This is the note content...</p>
    <p class="text-xs text-slate-500 mt-2">Added Jan 15, 2025</p>
  </div>
  
  <!-- Another note -->
  <div class="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
    <p class="text-slate-300 text-sm">Another note here...</p>
    <p class="text-xs text-slate-500 mt-2">Added Jan 10, 2025</p>
  </div>
  
  <!-- Add note form -->
  <form hx-post="/agent" hx-target="#content" class="mt-4">
    <textarea name="note_text" rows="2" placeholder="Add a note..."
              class="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white 
                     placeholder-slate-500 text-sm focus:outline-none focus:ring-2 
                     focus:ring-indigo-500 focus:border-transparent"></textarea>
    <input type="hidden" name="message" value="add note to book {book_id}">
    <button type="submit" 
            class="mt-2 px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-white 
                   rounded-lg transition-colors">
      Add Note
    </button>
  </form>
</div>
```

### Empty Notes State

```html
<div class="text-center py-6 text-slate-500">
  <p class="text-sm">No notes yet</p>
  <button hx-post="/agent" hx-target="#content" 
          hx-vals='{"message":"add note form for book {book_id}"}'
          class="mt-2 text-indigo-400 hover:text-indigo-300 text-sm">
    + Add first note
  </button>
</div>
```

---

## Aggregation Tool Response Pattern

For statistics/summary tools, use this response structure:

```python
@tool("get_statistics", "Get reading statistics", {})
def get_statistics() -> dict:
    books = load_books()
    
    # Compute aggregations
    total = len(books)
    by_status = {}
    for book in books:
        status = book.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
    
    rated_books = [b for b in books if b.get("rating")]
    avg_rating = sum(b["rating"] for b in rated_books) / len(rated_books) if rated_books else 0
    
    return {
        "type": "statistics",  # Hint for the agent about response type
        "summary": {
            "total_books": total,
            "by_status": by_status,
            "average_rating": round(avg_rating, 1),
            "rated_count": len(rated_books),
        },
        "details": {
            "want_to_read": by_status.get("want_to_read", 0),
            "reading": by_status.get("reading", 0),
            "finished": by_status.get("finished", 0),
        }
    }
```

The skill file should include guidance on rendering statistics:

```markdown
## Statistics Display

When showing statistics, use a grid of stat cards:

- Large number with label
- Color-code by meaning (emerald for positive, amber for in-progress)
- Include comparison or context where helpful
```
