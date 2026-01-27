# Saved Views - Progressive UI Caching

This reference documents the fast/slow path optimization pattern where users can save agent-generated views for instant loading.

## The Problem

Every user interaction calls the LLM, which is:
- **Slow**: 2-5 seconds per response
- **Expensive**: API costs add up
- **Redundant**: Many requests produce identical results

## The Solution: Two-Path Architecture

```
User Message → SavedViewsManager.find_matching_view()
                    ↓
              ┌─────┴─────┐
              │           │
         [Match Found]  [No Match]
              │           │
         FAST PATH    SLOW PATH
              │           │
    Return cached    Call Agent
    or template      Generate HTML
```

### Fast Path (Milliseconds)
- Check if message matches a saved view
- Return cached HTML or render template with fresh data
- No LLM call needed

### Slow Path (Seconds)
- Route to agent(s)
- Generate HTML response
- Optionally offer to save the view

## View Types

### 1. Static Views

For content that doesn't change:
- Welcome screens
- Forms
- Help pages
- Error templates

```python
# Static view caches the full HTML
view = views_manager.add_static_view(
    name="Add Book Form",
    trigger_phrases=["add a book", "new book", "add book"],
    keywords=["add", "new", "create"],
    html=agent_generated_html,
)
```

### 2. Data-Driven Views

For content that needs fresh data:
- Item lists
- Search results
- Statistics dashboards

```python
# Data-driven view caches a template with placeholders
view = views_manager.add_data_driven_view(
    name="My Books",
    trigger_phrases=["show my books", "list books"],
    keywords=["books", "list", "show"],
    html_template=template_with_placeholders,
    tools_needed=["list_books"],
)
```

Templates use placeholders like `{{BOOK_LIST}}` that are replaced with fresh data at serve time.

## Implementation

### SavedView Data Class

```python
# ABOUTME: Redesigned saved views with proper static vs data-driven separation.
# ABOUTME: Static views cache HTML directly; data-driven views use templates.

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from enum import Enum
import json


DATA_FILE = Path("data/saved_views.json")


class ViewType(str, Enum):
    STATIC = "static"           # Cache full HTML
    DATA_DRIVEN = "data-driven"  # Template + fresh data


@dataclass
class SavedView:
    """A user-saved view with proper caching semantics."""
    id: str
    name: str
    trigger_phrases: list[str]   # Exact matches (highest priority)
    keywords: list[str]          # All must be present (fallback)
    view_type: str               # "static" or "data-driven"
    html_template: str           # Full HTML or template with placeholders
    tools_needed: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    use_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SavedView":
        # Handle legacy views
        if "view_type" not in data:
            data["view_type"] = "static"
        if "tools_needed" not in data:
            data["tools_needed"] = []
        data.pop("has_dynamic_data", None)  # Remove legacy field
        return cls(**data)

    @property
    def is_static(self) -> bool:
        return self.view_type == ViewType.STATIC.value

    @property
    def is_data_driven(self) -> bool:
        return self.view_type == ViewType.DATA_DRIVEN.value
```

### SavedViewsManager

```python
class SavedViewsManager:
    """Manages saved views with proper static/data-driven handling."""

    def __init__(self):
        self._views: dict[str, SavedView] = {}
        self._load()

    def _load(self):
        """Load saved views from disk."""
        if not DATA_FILE.exists():
            return
        try:
            data = json.loads(DATA_FILE.read_text())
            self._views = {}
            for v in data.get("views", []):
                try:
                    view = SavedView.from_dict(v)
                    self._views[view.id] = view
                except Exception as e:
                    print(f"Skipping invalid view: {e}")
        except (json.JSONDecodeError, KeyError):
            self._views = {}

    def _save(self):
        """Save views to disk."""
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"views": [v.to_dict() for v in self._views.values()]}
        DATA_FILE.write_text(json.dumps(data, indent=2))

    def add_static_view(
        self,
        name: str,
        trigger_phrases: list[str],
        keywords: list[str],
        html: str,
    ) -> SavedView:
        """Add a static view (forms, welcome screens, etc.)."""
        view_id = f"static_{len(self._views) + 1}_{int(datetime.now().timestamp())}"

        view = SavedView(
            id=view_id,
            name=name,
            trigger_phrases=[p.lower().strip() for p in trigger_phrases],
            keywords=[k.lower().strip() for k in keywords],
            view_type=ViewType.STATIC.value,
            html_template=html,
            tools_needed=[],
        )

        self._views[view_id] = view
        self._save()
        return view

    def add_data_driven_view(
        self,
        name: str,
        trigger_phrases: list[str],
        keywords: list[str],
        html_template: str,
        tools_needed: list[str],
    ) -> SavedView:
        """Add a data-driven view with template and required tools."""
        view_id = f"dynamic_{len(self._views) + 1}_{int(datetime.now().timestamp())}"

        view = SavedView(
            id=view_id,
            name=name,
            trigger_phrases=[p.lower().strip() for p in trigger_phrases],
            keywords=[k.lower().strip() for k in keywords],
            view_type=ViewType.DATA_DRIVEN.value,
            html_template=html_template,
            tools_needed=tools_needed,
        )

        self._views[view_id] = view
        self._save()
        return view

    def find_matching_view(self, user_message: str) -> SavedView | None:
        """Find a saved view matching the user's message."""
        message_lower = user_message.lower().strip()

        # Exact phrase match (highest priority)
        for view in self._views.values():
            for phrase in view.trigger_phrases:
                if phrase == message_lower:
                    view.use_count += 1
                    self._save()
                    return view

        # Keyword match (all keywords must be present)
        for view in self._views.values():
            if view.keywords:
                if all(kw in message_lower for kw in view.keywords):
                    view.use_count += 1
                    self._save()
                    return view

        return None

    def get_view(self, view_id: str) -> SavedView | None:
        return self._views.get(view_id)

    def delete_view(self, view_id: str) -> bool:
        if view_id in self._views:
            del self._views[view_id]
            self._save()
            return True
        return False

    def list_views(self) -> list[SavedView]:
        """List all saved views, sorted by use count."""
        return sorted(
            self._views.values(),
            key=lambda v: v.use_count,
            reverse=True
        )

    def record_use(self, view_id: str):
        if view_id in self._views:
            self._views[view_id].use_count += 1
            self._save()


# Singleton
_manager: SavedViewsManager | None = None

def get_views_manager() -> SavedViewsManager:
    global _manager
    if _manager is None:
        _manager = SavedViewsManager()
    return _manager
```

### Template Rendering

```python
async def render_item_list_html(items: list[dict]) -> str:
    """Render a list of items as HTML."""
    if not items:
        return '''
<div class="text-center py-12 animate-in">
    <div class="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-4">
        <span class="text-2xl">📋</span>
    </div>
    <h3 class="text-lg font-semibold text-white mb-2">No items yet</h3>
    <p class="text-slate-400 mb-6">Start adding items!</p>
    <button hx-post="/agent" hx-target="#content" hx-indicator=".loading-indicator"
            hx-vals='{"message":"add an item"}'
            class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg">
        Add First Item
    </button>
</div>
'''

    html_items = []
    for item in items:
        item_id = item.get("id", "")
        name = item.get("name", "Unknown")
        description = item.get("description", "")
        status = item.get("status", "active")

        html_items.append(f'''
<div class="group flex items-center justify-between p-4 bg-slate-900 rounded-lg border border-slate-800
            hover:border-slate-700 hover:bg-slate-800/50 transition-all duration-200 cursor-pointer"
     hx-post="/agent" hx-target="#content" hx-indicator=".loading-indicator"
     hx-vals='{{"message":"show item {item_id}"}}'>
    <div class="flex items-center gap-4">
        <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center">
            <span class="text-white text-xl">📄</span>
        </div>
        <div>
            <p class="font-medium text-white group-hover:text-indigo-300 transition-colors">{name}</p>
            <p class="text-sm text-slate-400">{description[:50]}...</p>
        </div>
    </div>
    <div class="text-slate-400 group-hover:text-white transition-colors">→</div>
</div>
''')

    return '<div class="space-y-3">' + '\n'.join(html_items) + '</div>'


async def render_data_driven_view(view: SavedView, data: dict[str, Any]) -> str:
    """Render a data-driven view by replacing placeholders with fresh data."""
    html = view.html_template

    # Replace {{ITEM_COUNT}}
    if "{{ITEM_COUNT}}" in html:
        items = data.get("items", [])
        html = html.replace("{{ITEM_COUNT}}", str(len(items)))

    # Replace {{ITEM_LIST}}
    if "{{ITEM_LIST}}" in html:
        items = data.get("items", [])
        item_list_html = await render_item_list_html(items)
        html = html.replace("{{ITEM_LIST}}", item_list_html)

    # Replace {{STATS}}
    if "{{STATS}}" in html:
        stats = data.get("stats", {})
        html = html.replace("{{STATS}}", json.dumps(stats))

    return html
```

## FastAPI Integration

```python
from app.saved_views import (
    get_views_manager,
    render_data_driven_view,
    ViewType,
)
from app import database as db

views_manager = get_views_manager()


@app.post("/agent", response_class=HTMLResponse)
async def handle_message(request: Request):
    form_data = await request.form()
    message = str(form_data.get("message", "")).strip()

    if not message:
        return '<p class="text-amber-400">Please enter a message.</p>'

    # FAST PATH: Check for saved view match
    saved_view = views_manager.find_matching_view(message)
    if saved_view:
        if saved_view.is_static:
            # Static view: serve directly
            return saved_view.html_template
        else:
            # Data-driven view: fetch fresh data and render template
            items = await db.get_all_items()
            html = await render_data_driven_view(saved_view, {"items": items})
            return html

    # SLOW PATH: Call agent
    try:
        html = await router.process_user_message(message)
        # Wrap response with save option
        html = _wrap_with_save_option(html, message)
        return html
    except Exception as e:
        return f'<p class="text-red-400">Error: {e}</p>'


def _wrap_with_save_option(html: str, original_message: str) -> str:
    """Wrap agent-generated HTML with a save button."""
    import html as html_escape
    escaped_message = html_escape.escape(original_message)
    save_button = f'''
<div class="mt-4 pt-4 border-t border-slate-800 flex justify-end">
    <button onclick="showSaveModal('{escaped_message}')"
            class="text-xs text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1">
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/>
        </svg>
        Save this view
    </button>
</div>
'''
    return html + save_button
```

## Save View Modal (HTML)

> **Security Note**: The JavaScript below uses element.value (not innerHTML) to capture
> the current view content. In production, consider sanitizing any user-submitted HTML
> with a library like DOMPurify before storage or display.

```html
<!-- Save View Modal -->
<div id="save-modal" class="hidden fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
    <div class="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-md mx-4 animate-in">
        <div class="p-5 border-b border-slate-800">
            <h3 class="text-lg font-bold font-['Space_Grotesk'] text-white">Save This View</h3>
            <p class="text-slate-400 text-sm mt-1">Save for instant access next time</p>
        </div>
        <form id="save-view-form" class="p-5 space-y-4">
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">View Name</label>
                <input type="text" name="name" required placeholder="e.g., My Items"
                       class="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white
                              placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500">
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Trigger Phrase</label>
                <input type="text" name="trigger_phrase" id="save-trigger" required
                       class="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white
                              placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                <p class="text-xs text-slate-500 mt-1">Type this exactly to load this view instantly</p>
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Keywords (optional)</label>
                <input type="text" name="keywords" placeholder="items, list, show"
                       class="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white
                              placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                <p class="text-xs text-slate-500 mt-1">Comma-separated words that should trigger this view</p>
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">View Type</label>
                <div class="space-y-2">
                    <label class="flex items-start gap-3 p-3 bg-slate-800 rounded-lg cursor-pointer hover:bg-slate-700">
                        <input type="radio" name="view_type" value="static" checked
                               class="mt-1 w-4 h-4 text-indigo-600 focus:ring-indigo-500">
                        <div>
                            <p class="text-white font-medium">Static</p>
                            <p class="text-xs text-slate-400">For forms, welcome screens. Caches exact HTML.</p>
                        </div>
                    </label>
                    <label class="flex items-start gap-3 p-3 bg-slate-800 rounded-lg cursor-pointer hover:bg-slate-700">
                        <input type="radio" name="view_type" value="data-driven"
                               class="mt-1 w-4 h-4 text-indigo-600 focus:ring-indigo-500">
                        <div>
                            <p class="text-white font-medium">Data-driven</p>
                            <p class="text-xs text-slate-400">For lists. Uses template + fetches fresh data.</p>
                        </div>
                    </label>
                </div>
            </div>
            <input type="hidden" name="html_template" id="save-html">
        </form>
        <div class="p-5 border-t border-slate-800 flex justify-end gap-3">
            <button onclick="closeSaveModal()"
                    class="px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg">
                Cancel
            </button>
            <button onclick="submitSaveView()"
                    class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
                           shadow-lg shadow-indigo-500/25 transition-all">
                Save View
            </button>
        </div>
    </div>
</div>

<script>
// Note: This uses element.value for the hidden input, which is safe.
// The contentDiv content comes from the agent (server-generated), not user input.
// For production use with untrusted content, sanitize HTML before storage.
function showSaveModal(triggerPhrase) {
    const modal = document.getElementById('save-modal');
    const triggerInput = document.getElementById('save-trigger');
    const contentDiv = document.getElementById('content');
    const htmlInput = document.getElementById('save-html');

    triggerInput.value = triggerPhrase;
    // Capture current view content (agent-generated, not user input)
    htmlInput.value = contentDiv.outerHTML;
    modal.classList.remove('hidden');
}

function closeSaveModal() {
    document.getElementById('save-modal').classList.add('hidden');
}

function submitSaveView() {
    const form = document.getElementById('save-view-form');
    const formData = new FormData(form);

    fetch('/views/save', {
        method: 'POST',
        body: formData
    })
    .then(response => response.text())
    .then(html => {
        // Update content with server response (sanitized on server)
        document.getElementById('content').outerHTML =
            '<div id="content">' + html + '</div>';
        closeSaveModal();
    })
    .catch(err => console.error('Save failed:', err));
}
</script>
```

## Converting Agent HTML to Template

When saving a data-driven view, convert the agent's HTML to a template:

```python
def _convert_to_template(html: str) -> str:
    """Convert agent-generated HTML to a template with placeholders."""
    import re

    # Find and replace the item list div with placeholder
    pattern = r'<div class="space-y-3">.*?</div>\s*(?=<div class="mt-4|$)'

    if re.search(pattern, html, re.DOTALL):
        template = re.sub(pattern, '{{ITEM_LIST}}\n', html, flags=re.DOTALL)
    else:
        # Fallback: append placeholder at end
        template = html + '\n{{ITEM_LIST}}'

    # Replace hardcoded counts with placeholders
    template = re.sub(r'\d+ items? total', '{{ITEM_COUNT}} items total', template)

    return template
```

## Benefits

1. **Faster UX**: Cached views load instantly
2. **Cost Savings**: Fewer LLM API calls
3. **User Empowerment**: Users save the views they actually use
4. **Fresh Data**: Data-driven views always show current data
5. **Observability**: Track which views are used most (use_count)

## Anti-Patterns to Avoid

### Don't Cache Dynamic Data as Static

```python
# WRONG: Caching a list as static means stale data
view = views_manager.add_static_view(
    name="My Items",
    trigger_phrases=["show items"],
    html=list_html_with_current_items,  # This will be stale!
)

# RIGHT: Use data-driven for lists
view = views_manager.add_data_driven_view(
    name="My Items",
    trigger_phrases=["show items"],
    html_template=template_with_placeholder,
    tools_needed=["list_items"],
)
```

### Do Use Static for Forms

```python
# RIGHT: Forms don't have dynamic data
view = views_manager.add_static_view(
    name="Add Item Form",
    trigger_phrases=["add item", "new item", "create item"],
    html=add_item_form_html,
)
```
