# Hexagonal Architecture for AI Agent Applications

This document provides a deep dive into the hexagonal (ports-and-adapters) architecture pattern and why it's well-suited for AI agent applications.

---

## What is Hexagonal Architecture?

Hexagonal architecture, introduced by Alistair Cockburn in 2005, organizes applications around a central domain core, with external concerns connected through well-defined ports and adapters.

```
                    ┌─────────────────────────────────┐
                    │                                 │
     HTTP ─────────►│◄────── Port ──────►│           │
                    │                    │           │
    WebSocket ─────►│◄────── Port ──────►│  Domain   │
                    │                    │   Core    │
     CLI ──────────►│◄────── Port ──────►│  (Agent)  │
                    │                    │           │
    Database ◄─────►│◄────── Port ──────►│           │
                    │                                 │
                    └─────────────────────────────────┘
```

**Key concepts:**

- **Domain Core**: Business logic lives here. In our case, the agent's reasoning and UI generation.
- **Ports**: Interfaces that define how the core interacts with the outside world. Either driving (input) or driven (output).
- **Adapters**: Implementations that connect external systems to ports. Can be swapped without changing the core.

---

## Why Hexagonal Architecture Fits AI Agents

### 1. Natural Separation of Concerns

AI agents naturally have three concerns:

| Concern | Traditional Code | Hexagonal Agent |
|---------|-----------------|-----------------|
| Data Access | Repository classes | MCP Tools (driven port) |
| Business Logic | Service classes | Agent reasoning |
| Presentation | Controllers/Views | HTML generation |

The agent's skill file teaches it how to combine data access (tools) with presentation (HTML generation). The HTTP adapter handles transport.

### 2. Tool as Driven Port

MCP tools are perfect driven ports:

```python
@tool("list_books", "Get all books", {})
async def list_books(args):
    # This is a PORT - the implementation can change
    return fetch_from_database()
    # or: return fetch_from_api()
    # or: return fetch_from_memory()
```

The agent doesn't know or care where data comes from. It calls the tool and renders results.

### 3. HTTP as Driving Port

FastAPI serves as the driving adapter:

```python
@app.post("/agent")
async def handle_message(request: Request):
    message = extract_message(request)
    html = await agent.process(message)  # Port: agent interface
    return html
```

Tomorrow you could add a WebSocket adapter, CLI adapter, or Slack adapter. The agent core doesn't change.

### 4. Testability

Each boundary is testable in isolation:

```python
# Test tools directly
result = await list_books({})
assert len(result["books"]) == 3

# Test agent with mock tools
mock_server = create_mock_server([mock_list_books])
agent = Agent(tools_server=mock_server)
html = await agent.process("show books")
assert "The Hobbit" in html

# Test HTTP adapter with mock agent
app.dependency_overrides[get_agent] = lambda: mock_agent
response = client.post("/agent", data={"message": "show books"})
assert response.status_code == 200
```

---

## Comparison to Traditional MVC

| Aspect | MVC | Hexagonal Agent |
|--------|-----|-----------------|
| View rendering | Templates compiled at build time | Generated at runtime by agent |
| Controller logic | Hard-coded if/else | Semantic interpretation |
| Model changes | Requires view updates | Agent adapts automatically |
| New features | New controllers, views, tests | New tools, skill updates |
| Error handling | Try/catch, error pages | Agent explains in natural language |

The agent acts as an intelligent adapter layer that can handle variations in user input that traditional controllers would need explicit code for.

---

## The "Prompt Object" Model

In Smalltalk, objects respond to messages. The sender doesn't know how the message will be handled—that's the receiver's responsibility. This is "semantic late binding."

AI agents work the same way:

```
Traditional code:
  user clicks "Add Book" button
  → router dispatches to BooksController#create
  → controller validates, saves, redirects

Hexagonal agent:
  user says "add The Hobbit to my reading list"
  → agent interprets semantic intent
  → agent decides: call create_book tool
  → agent generates: success UI with the book
```

The agent is a "prompt object" that receives semantic messages and decides how to respond. This provides flexibility that traditional code cannot match.

---

## Extension Points

### Adding a New Tool

1. Define the tool in `tools.py`
2. Add to `create_tools_server()`
3. Add to agent's `allowed_tools` list
4. Document in skill file

The agent automatically starts using it based on user intent.

### Adding a New Adapter

Create a new driving adapter:

```python
# cli_adapter.py
async def main():
    agent = Agent()
    while True:
        message = input("> ")
        html = await agent.process(message)
        # Convert HTML to terminal output
        print(render_to_terminal(html))
```

The agent core doesn't change.

### Changing Data Storage

Replace the tool implementation:

```python
# Before: JSON file
def _load_data():
    return json.loads(DATA_FILE.read_text())

# After: PostgreSQL
def _load_data():
    return db.query(Book).all()
```

The agent doesn't know the difference.

---

## Architectural Boundaries

### Boundary 1: User → HTTP Adapter

**Crossing**: HTTP POST with form data
**Data**: `message` string + form fields
**Responsibility**: Parse request, extract message, call agent

### Boundary 2: HTTP Adapter → Agent

**Crossing**: Method call `agent.process(message)`
**Data**: Natural language string
**Responsibility**: Interpret intent, call tools, generate HTML

### Boundary 3: Agent → Tools (MCP)

**Crossing**: Tool invocation via MCP protocol
**Data**: Tool name + JSON arguments
**Responsibility**: Execute data operation, return structured JSON

### Boundary 4: Agent → User (via HTTP Adapter)

**Crossing**: HTML string return
**Data**: HTML fragment for HTMX swap
**Responsibility**: Display in browser

---

## When to Use This Pattern

**Good fit:**

- CRUD applications with conversational interface
- Internal tools where users have varied requests
- Prototypes that need to adapt quickly
- Applications where UI flexibility matters more than pixel precision

**Poor fit:**

- High-traffic public applications (LLM latency, cost)
- Applications requiring precise pixel-perfect design
- Real-time applications (games, trading)
- Offline-first applications

---

## Summary

Hexagonal architecture provides clean separation for AI agent applications:

1. **Agent** = Domain core (reasoning + UI generation)
2. **Tools** = Driven ports (data operations)
3. **HTTP** = Driving adapter (user interface)

This separation enables:

- Easy testing at each boundary
- Swappable implementations
- Evolution without breaking changes
- Natural AI-human collaboration

The agent interprets user intent semantically rather than requiring exact commands, providing flexibility that traditional architectures cannot match.
