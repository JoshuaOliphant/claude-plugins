"""
ABOUTME: FastAPI application for hexagonal agent applications.
ABOUTME: The HTTP adapter that routes user messages to the agent.

Key responsibilities:
1. Serve the base HTML template (the "shell")
2. Handle /agent POST requests (user messages)
3. Return HTML fragments for HTMX to swap
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from app.agent import Agent

# Create the agent instance
agent = Agent()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - cleanup on shutdown."""
    yield
    await agent.close()


app = FastAPI(lifespan=lifespan)


# === Base HTML Template ===
# This is the "shell" that wraps agent-generated content.
# It includes: CSS (Tailwind), HTMX, persistent UI elements.

BASE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>

    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>

    <!-- Custom styles -->
    <style>
        /* Loading states */
        .htmx-request .loading-indicator {{ display: flex; }}
        .htmx-request #content {{ opacity: 0.6; pointer-events: none; }}
        .loading-indicator {{ display: none; }}

        /* Animation */
        @keyframes fadeSlideIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .animate-in {{ animation: fadeSlideIn 0.3s ease-out; }}

        /* Staggered animations */
        .stagger-1 {{ animation-delay: 0.05s; }}
        .stagger-2 {{ animation-delay: 0.1s; }}
        .stagger-3 {{ animation-delay: 0.15s; }}
    </style>
</head>
<body class="min-h-screen bg-slate-950 text-slate-100">
    <!-- Header -->
    <nav class="bg-slate-900 border-b border-slate-800">
        <div class="max-w-4xl mx-auto px-4 py-3 flex justify-between items-center">
            <h1 class="text-xl font-bold font-['Space_Grotesk']">{title}</h1>
            <button hx-post="/reset" hx-target="#content"
                    class="text-sm text-slate-400 hover:text-white transition-colors">
                Reset
            </button>
        </div>
    </nav>

    <!-- Main content area - HTMX swaps content here -->
    <main class="max-w-4xl mx-auto p-4">
        <!-- Loading indicator -->
        <div class="loading-indicator items-center justify-center py-8">
            <svg class="animate-spin h-8 w-8 text-indigo-500" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
        </div>

        <!-- Content target -->
        <div id="content">
            {content}
        </div>
    </main>

    <!-- Input area (fixed at bottom) -->
    <footer class="fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-800">
        <form hx-post="/agent" hx-target="#content" class="max-w-4xl mx-auto p-4 flex gap-3">
            <input type="text" name="message"
                   placeholder="What would you like to do?"
                   autocomplete="off"
                   class="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                          text-white placeholder-slate-500
                          focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                          transition-all duration-200">
            <button type="submit"
                    class="px-6 py-2 bg-indigo-600 hover:bg-indigo-500
                           text-white font-medium rounded-lg transition-colors
                           shadow-lg shadow-indigo-500/25">
                Send
            </button>
        </form>
    </footer>

    <!-- Spacer for fixed footer -->
    <div class="h-24"></div>

    <!-- Scripts -->
    <script>
        // Clear input after submission
        document.body.addEventListener('htmx:afterRequest', function(event) {{
            if (event.detail.elt.matches('form')) {{
                const input = event.detail.elt.querySelector('input[name="message"]');
                if (input) input.value = '';
            }}
        }});

        // Focus input on load
        document.querySelector('input[name="message"]')?.focus();
    </script>
</body>
</html>'''


# Welcome content shown on initial load
WELCOME_CONTENT = '''
<div class="text-center py-16 animate-in">
    <div class="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-4">
        <span class="text-2xl">✨</span>
    </div>
    <h2 class="text-2xl font-bold font-['Space_Grotesk'] text-white mb-4">Welcome</h2>
    <p class="text-slate-400 mb-8">What would you like to do today?</p>
    <div class="flex flex-wrap justify-center gap-3">
        <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"show my items"}'
                class="px-4 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors">
            View Items
        </button>
        <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"create a new item"}'
                class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors
                       shadow-lg shadow-indigo-500/25">
            Create Item
        </button>
    </div>
</div>
'''


# === Routes ===

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main page."""
    return BASE_TEMPLATE.format(
        title="My App",
        content=WELCOME_CONTENT
    )


@app.post("/agent", response_class=HTMLResponse)
async def handle_message(request: Request):
    """
    Handle user messages sent to the agent.

    This receives:
    - message: The user's text input OR hidden message from buttons/forms
    - Other form fields: Any additional data from forms

    Returns:
    - HTML fragment to be swapped into #content by HTMX
    """
    # Get all form data
    form_data = await request.form()

    # Extract the message
    message = form_data.get("message", "")
    if not message or not str(message).strip():
        return '<p class="text-amber-400">Please enter a message.</p>'

    message = str(message).strip()

    # If there are additional form fields, append them to the message
    # This handles form submissions with field values
    extra_fields = []
    for key, value in form_data.items():
        if key != "message" and value:
            extra_fields.append(f"{key}={value}")

    if extra_fields:
        message = f"{message} [{', '.join(extra_fields)}]"

    try:
        html = await agent.process(message)
        return html
    except Exception as e:
        # Log the error in production
        print(f"Agent error: {e}")
        return '''
<div class="p-4 bg-red-500/10 border border-red-500/30 rounded-lg animate-in">
    <p class="text-red-300">✗ An error occurred. Please try again.</p>
</div>
'''


@app.post("/reset", response_class=HTMLResponse)
async def reset():
    """Reset conversation state and return to welcome screen."""
    await agent.reset()
    return WELCOME_CONTENT
