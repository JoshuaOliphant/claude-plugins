# Enhanced UX Patterns

This reference documents UX improvements for hexagonal agent apps, including better loading states, form handling, and visual feedback.

## The Problem

Agent responses take 2-5 seconds. Default HTMX loading indicators are minimal:
- User doesn't know if anything is happening
- No visual feedback during processing
- Form can be submitted multiple times
- Content jump when response arrives

## Enhanced Loading State

### Animated Multi-Stage Indicator

```html
<div class="loading-indicator flex-col items-center justify-center py-12">
    <div class="bg-slate-900 rounded-xl border border-slate-700 p-6 shadow-xl shadow-indigo-500/10">
        <!-- Spinner + Title -->
        <div class="flex items-center justify-center gap-3 mb-4">
            <svg class="animate-spin h-6 w-6 text-indigo-500" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            <span class="text-white font-medium">Agents Working</span>
        </div>

        <!-- Bouncing Dots (agent activity) -->
        <div class="flex items-center justify-center gap-2 text-sm">
            <span class="agent-dot w-2 h-2 bg-indigo-400 rounded-full"></span>
            <span class="agent-dot w-2 h-2 bg-purple-400 rounded-full"></span>
            <span class="agent-dot w-2 h-2 bg-pink-400 rounded-full"></span>
        </div>

        <!-- Cycling Status Message -->
        <p class="text-slate-400 text-sm mt-3 text-center animate-pulse">
            Processing your request...
        </p>
    </div>
</div>
```

### CSS Animations

```css
<style>
    /* Show loading indicator during HTMX request */
    .loading-indicator.htmx-request { display: flex !important; }
    .loading-indicator { display: none; }

    /* Fade-slide animation for content */
    @keyframes fadeSlideIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .animate-in { animation: fadeSlideIn 0.3s ease-out; }

    /* Pulse animation for status text */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    .animate-pulse { animation: pulse 1.5s ease-in-out infinite; }

    /* Bouncing dots for agent activity */
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-4px); }
    }
    .agent-dot { animation: bounce 0.6s ease-in-out infinite; }
    .agent-dot:nth-child(2) { animation-delay: 0.1s; }
    .agent-dot:nth-child(3) { animation-delay: 0.2s; }

    /* Show/hide for HTMX indicator elements */
    .htmx-request .htmx-indicator { display: inline !important; }
    .htmx-request .htmx-indicator-hide { display: none !important; }
    .htmx-indicator { display: none; }
</style>
```

### JavaScript: Cycling Status Messages

```javascript
<script>
// Loading messages that cycle during agent processing
const loadingMessages = [
    "Processing your request...",
    "UI Agent analyzing intent...",
    "Consulting specialist agents...",
    "Generating response...",
    "Almost there..."
];
let messageIndex = 0;
let messageInterval = null;

document.body.addEventListener('htmx:beforeRequest', function(event) {
    // Show loading indicator for all requests
    const indicator = document.querySelector('.loading-indicator');
    const content = document.getElementById('content');

    if (indicator) {
        indicator.style.display = 'flex';
    }
    if (content) {
        content.style.opacity = '0.3';
        content.style.pointerEvents = 'none';
        content.style.filter = 'blur(1px)';
    }

    // Start cycling through loading messages
    const loadingText = document.querySelector('.loading-indicator .animate-pulse');
    if (loadingText) {
        messageIndex = 0;
        loadingText.textContent = loadingMessages[0];
        messageInterval = setInterval(() => {
            messageIndex = (messageIndex + 1) % loadingMessages.length;
            loadingText.textContent = loadingMessages[messageIndex];
        }, 1500);
    }
});

document.body.addEventListener('htmx:afterRequest', function(event) {
    // Hide loading indicator
    const indicator = document.querySelector('.loading-indicator');
    const content = document.getElementById('content');

    if (indicator) {
        indicator.style.display = 'none';
    }
    if (content) {
        content.style.opacity = '1';
        content.style.pointerEvents = 'auto';
        content.style.filter = 'none';
    }

    // Stop the message cycling
    if (messageInterval) {
        clearInterval(messageInterval);
        messageInterval = null;
    }

    // Clear form input
    if (event.detail.elt.matches('form')) {
        const input = event.detail.elt.querySelector('input[name="message"]');
        if (input) input.value = '';
    }
});

// Auto-focus the message input on page load
document.querySelector('input[name="message"]')?.focus();
</script>
```

## Form Disabling During Requests

Prevent double-submission and show visual feedback:

```html
<form hx-post="/agent" hx-target="#content" hx-indicator=".loading-indicator"
      class="max-w-4xl mx-auto p-4 flex gap-3">

    <!-- Input with disabled state -->
    <input type="text" name="message"
           placeholder="What would you like to do?"
           autocomplete="off"
           class="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                  text-white placeholder-slate-500
                  focus:outline-none focus:ring-2 focus:ring-indigo-500
                  disabled:opacity-50 disabled:cursor-not-allowed"
           hx-disabled-elt="this">

    <!-- Button with loading spinner -->
    <button type="submit"
            class="px-6 py-2 bg-indigo-600 hover:bg-indigo-500
                   text-white font-medium rounded-lg transition-colors
                   disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-indigo-600"
            hx-disabled-elt="this">

        <!-- Text shown when not loading -->
        <span class="htmx-indicator-hide">Send</span>

        <!-- Spinner shown when loading -->
        <span class="htmx-indicator hidden">
            <svg class="animate-spin h-5 w-5 inline" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10"
                        stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
        </span>
    </button>
</form>
```

Key HTMX attributes:
- `hx-indicator=".loading-indicator"` - Show loading indicator during request
- `hx-disabled-elt="this"` - Disable this element during request

## Content Dimming

During loading, dim the existing content to show it's stale:

```javascript
// In htmx:beforeRequest
if (content) {
    content.style.opacity = '0.3';      // Dim content
    content.style.pointerEvents = 'none'; // Prevent clicks
    content.style.filter = 'blur(1px)';   // Subtle blur
}

// In htmx:afterRequest
if (content) {
    content.style.opacity = '1';
    content.style.pointerEvents = 'auto';
    content.style.filter = 'none';
}
```

## Enhanced Welcome Screen

Make the welcome screen engaging and action-oriented:

```html
<div class="text-center py-16 animate-in">
    <!-- Gradient Icon -->
    <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-600
                flex items-center justify-center mx-auto mb-6
                shadow-lg shadow-indigo-500/30">
        <span class="text-4xl">📚</span>
    </div>

    <!-- Title -->
    <h2 class="text-3xl font-bold font-['Space_Grotesk'] text-white mb-4">
        Welcome to Your Reading List
    </h2>

    <!-- Description -->
    <p class="text-slate-400 mb-8 max-w-md mx-auto">
        Track the books you want to read, are reading, and have finished.
        Rate and review your favorites!
    </p>

    <!-- Multi-Agent Badge -->
    <div class="mb-8 p-4 bg-slate-900/50 rounded-xl border border-slate-800 max-w-lg mx-auto">
        <p class="text-sm text-purple-400 mb-2">🤖 Multi-Agent System</p>
        <p class="text-xs text-slate-500">UI Agent • Recommender Agent • Insights Agent</p>
    </div>

    <!-- Action Buttons -->
    <div class="flex flex-wrap justify-center gap-4">
        <!-- Secondary Action -->
        <button hx-post="/agent" hx-target="#content" hx-indicator=".loading-indicator"
                hx-vals='{"message":"show my books"}'
                class="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700
                       rounded-lg transition-colors font-medium">
            📖 View My Books
        </button>

        <!-- Primary Action -->
        <button hx-post="/agent" hx-target="#content" hx-indicator=".loading-indicator"
                hx-vals='{"message":"add a book"}'
                class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg
                       transition-colors font-medium shadow-lg shadow-indigo-500/25">
            + Add a Book
        </button>

        <!-- Feature Action -->
        <button hx-post="/agent" hx-target="#content" hx-indicator=".loading-indicator"
                hx-vals='{"message":"what should I read next"}'
                class="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 rounded-lg
                       transition-colors font-medium shadow-lg shadow-purple-500/25">
            🎯 Get Recommendations
        </button>

        <!-- Analytics Action -->
        <button hx-post="/agent" hx-target="#content" hx-indicator=".loading-indicator"
                hx-vals='{"message":"analyze my reading patterns"}'
                class="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700
                       rounded-lg transition-colors font-medium">
            📊 Reading Insights
        </button>
    </div>
</div>
```

## Navigation Header

Clean header with debug access:

```html
<nav class="bg-slate-900 border-b border-slate-800">
    <div class="max-w-4xl mx-auto px-4 py-3 flex justify-between items-center">
        <!-- Title -->
        <h1 class="text-xl font-bold font-['Space_Grotesk']">Reading List</h1>

        <div class="flex items-center gap-4">
            <!-- Saved Views -->
            <button hx-get="/views/list" hx-target="#content"
                    class="text-sm text-purple-400 hover:text-purple-300 transition-colors
                           flex items-center gap-1">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/>
                </svg>
                Saved Views
            </button>

            <!-- Debug Link (opens in new tab) -->
            <a href="/debug/messages" target="_blank"
               class="text-xs text-slate-500 hover:text-slate-400 transition-colors">
                Debug
            </a>

            <!-- Reset -->
            <button hx-post="/reset" hx-target="#content"
                    class="text-sm text-slate-400 hover:text-white transition-colors">
                Reset
            </button>
        </div>
    </div>
</nav>
```

## Status Badges

Color-coded status indicators:

```html
<!-- Status badge classes -->
<style>
    .badge-want-to-read {
        @apply bg-blue-500/20 text-blue-400 border-blue-500/30;
    }
    .badge-reading {
        @apply bg-amber-500/20 text-amber-400 border-amber-500/30;
    }
    .badge-finished {
        @apply bg-emerald-500/20 text-emerald-400 border-emerald-500/30;
    }
</style>

<!-- Usage -->
<span class="px-2.5 py-1 text-xs font-medium rounded-full border badge-reading">
    Reading
</span>
```

Python helper for generating badges:

```python
STATUS_STYLES = {
    "want-to-read": {
        "class": "bg-blue-500/20 text-blue-400 border-blue-500/30",
        "label": "Want to Read",
    },
    "reading": {
        "class": "bg-amber-500/20 text-amber-400 border-amber-500/30",
        "label": "Reading",
    },
    "finished": {
        "class": "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
        "label": "Finished",
    },
    "active": {
        "class": "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
        "label": "Active",
    },
    "archived": {
        "class": "bg-slate-500/20 text-slate-400 border-slate-500/30",
        "label": "Archived",
    },
}


def get_status_badge(status: str) -> str:
    """Generate HTML for a status badge."""
    style = STATUS_STYLES.get(status, STATUS_STYLES["active"])
    return f'''
<span class="px-2.5 py-1 text-xs font-medium rounded-full border {style["class"]}">
    {style["label"]}
</span>
'''
```

## Rating Stars

Interactive star rating display:

```python
def get_rating_stars(rating: int | None) -> str:
    """Generate HTML for star rating display."""
    if rating is None:
        return '<span class="text-slate-500 text-sm">Not rated</span>'

    filled = "★" * rating
    empty = "★" * (5 - rating)

    return f'''
<div class="flex items-center gap-0.5 text-sm">
    <span class="text-amber-400">{filled}</span>
    <span class="text-slate-600">{empty}</span>
</div>
'''
```

## Empty States

Encouraging empty states with clear call-to-action:

```html
<div class="text-center py-12 animate-in">
    <div class="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-4">
        <span class="text-2xl">📚</span>
    </div>
    <h3 class="text-lg font-semibold text-white mb-2">No books yet</h3>
    <p class="text-slate-400 mb-6">Start building your reading list!</p>
    <button hx-post="/agent" hx-target="#content" hx-indicator=".loading-indicator"
            hx-vals='{"message":"add a book"}'
            class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
                   shadow-lg shadow-indigo-500/25 transition-all">
        Add Your First Book
    </button>
</div>
```

## Success Feedback

Show success with auto-dismiss option:

```html
<div class="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg animate-in mb-4">
    <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
            <span class="text-emerald-400">✓</span>
        </div>
        <div>
            <p class="text-emerald-300 font-medium">Book added!</p>
            <p class="text-slate-400 text-sm">"The Great Gatsby" is now in your reading list</p>
        </div>
    </div>
</div>
```

## Error Feedback

Clear error messages with recovery actions:

```html
<div class="p-4 bg-red-500/10 border border-red-500/30 rounded-lg animate-in">
    <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0">
            <span class="text-red-400">✕</span>
        </div>
        <div>
            <p class="text-red-300 font-medium">Something went wrong</p>
            <p class="text-slate-400 text-sm mb-3">We couldn't process your request. Please try again.</p>
            <button hx-post="/agent" hx-target="#content"
                    hx-vals='{"message":"show my books"}'
                    class="text-sm text-slate-400 hover:text-white transition-colors">
                ← Back to list
            </button>
        </div>
    </div>
</div>
```

## Complete BASE_TEMPLATE

Putting it all together:

```python
BASE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My App</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
    <style>
        .loading-indicator.htmx-request {{ display: flex !important; }}
        .loading-indicator {{ display: none; }}
        @keyframes fadeSlideIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .animate-in {{ animation: fadeSlideIn 0.3s ease-out; }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .animate-pulse {{ animation: pulse 1.5s ease-in-out infinite; }}
        @keyframes bounce {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-4px); }}
        }}
        .agent-dot {{ animation: bounce 0.6s ease-in-out infinite; }}
        .agent-dot:nth-child(2) {{ animation-delay: 0.1s; }}
        .agent-dot:nth-child(3) {{ animation-delay: 0.2s; }}
        .htmx-request .htmx-indicator {{ display: inline !important; }}
        .htmx-request .htmx-indicator-hide {{ display: none !important; }}
        .htmx-indicator {{ display: none; }}
    </style>
</head>
<body class="min-h-screen bg-slate-950 text-slate-100">
    <nav class="bg-slate-900 border-b border-slate-800">
        <div class="max-w-4xl mx-auto px-4 py-3 flex justify-between items-center">
            <h1 class="text-xl font-bold font-['Space_Grotesk']">My App</h1>
            <div class="flex items-center gap-4">
                <a href="/debug/messages" target="_blank"
                   class="text-xs text-slate-500 hover:text-slate-400 transition-colors">
                    Debug
                </a>
                <button hx-post="/reset" hx-target="#content"
                        class="text-sm text-slate-400 hover:text-white transition-colors">
                    Reset
                </button>
            </div>
        </div>
    </nav>

    <main class="max-w-4xl mx-auto p-4">
        <div class="loading-indicator flex-col items-center justify-center py-12">
            <div class="bg-slate-900 rounded-xl border border-slate-700 p-6 shadow-xl shadow-indigo-500/10">
                <div class="flex items-center justify-center gap-3 mb-4">
                    <svg class="animate-spin h-6 w-6 text-indigo-500" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                    </svg>
                    <span class="text-white font-medium">Processing</span>
                </div>
                <div class="flex items-center justify-center gap-2">
                    <span class="agent-dot w-2 h-2 bg-indigo-400 rounded-full"></span>
                    <span class="agent-dot w-2 h-2 bg-purple-400 rounded-full"></span>
                    <span class="agent-dot w-2 h-2 bg-pink-400 rounded-full"></span>
                </div>
                <p class="text-slate-400 text-sm mt-3 text-center animate-pulse">
                    Processing your request...
                </p>
            </div>
        </div>

        <div id="content">
            {{content}}
        </div>
    </main>

    <footer class="fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-800">
        <form hx-post="/agent" hx-target="#content" hx-indicator=".loading-indicator"
              class="max-w-4xl mx-auto p-4 flex gap-3">
            <input type="text" name="message"
                   placeholder="What would you like to do?"
                   autocomplete="off"
                   class="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                          text-white placeholder-slate-500
                          focus:outline-none focus:ring-2 focus:ring-indigo-500
                          disabled:opacity-50 disabled:cursor-not-allowed"
                   hx-disabled-elt="this">
            <button type="submit"
                    class="px-6 py-2 bg-indigo-600 hover:bg-indigo-500
                           text-white font-medium rounded-lg transition-colors
                           disabled:opacity-50 disabled:cursor-not-allowed"
                    hx-disabled-elt="this">
                <span class="htmx-indicator-hide">Send</span>
                <span class="htmx-indicator hidden">
                    <svg class="animate-spin h-5 w-5 inline" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                    </svg>
                </span>
            </button>
        </form>
    </footer>

    <div class="h-24"></div>

    <script>
        const loadingMessages = [
            "Processing your request...",
            "Agent analyzing intent...",
            "Generating response...",
            "Almost there..."
        ];
        let messageIndex = 0;
        let messageInterval = null;

        document.body.addEventListener('htmx:beforeRequest', function(event) {{
            const indicator = document.querySelector('.loading-indicator');
            const content = document.getElementById('content');
            if (indicator) indicator.style.display = 'flex';
            if (content) {{
                content.style.opacity = '0.3';
                content.style.pointerEvents = 'none';
                content.style.filter = 'blur(1px)';
            }}

            const loadingText = document.querySelector('.loading-indicator .animate-pulse');
            if (loadingText) {{
                messageIndex = 0;
                loadingText.textContent = loadingMessages[0];
                messageInterval = setInterval(() => {{
                    messageIndex = (messageIndex + 1) % loadingMessages.length;
                    loadingText.textContent = loadingMessages[messageIndex];
                }}, 1500);
            }}
        }});

        document.body.addEventListener('htmx:afterRequest', function(event) {{
            const indicator = document.querySelector('.loading-indicator');
            const content = document.getElementById('content');
            if (indicator) indicator.style.display = 'none';
            if (content) {{
                content.style.opacity = '1';
                content.style.pointerEvents = 'auto';
                content.style.filter = 'none';
            }}
            if (messageInterval) {{
                clearInterval(messageInterval);
                messageInterval = null;
            }}
            if (event.detail.elt.matches('form')) {{
                const input = event.detail.elt.querySelector('input[name="message"]');
                if (input) input.value = '';
            }}
        }});

        document.querySelector('input[name="message"]')?.focus();
    </script>
</body>
</html>'''
```

## Benefits

1. **Clear Feedback** - Users know something is happening
2. **No Double-Submit** - Form disabled during request
3. **Professional Feel** - Animations and polish
4. **Accessibility** - Proper disabled states
5. **Debugging** - Easy access to message logs
