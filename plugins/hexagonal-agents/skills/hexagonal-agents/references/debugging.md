# Debugging Hexagonal Agent Applications

Common issues and fixes when building hexagonal agent apps.

## Agent outputs markdown instead of HTML

**Symptom:** Response wrapped in ```html ... ```

**Fix:**
1. Verify skill file has "Output ONLY raw HTML" rule prominently
2. Add reminder at end of system prompt: "Never use markdown code fences"
3. The agent's `_clean_html` method strips fences as fallback

## Tool not being called

**Symptom:** Agent responds conversationally instead of using tools

**Fix:**
1. Check tool is in `allowed_tools` list (exact format: `mcp__servername__toolname`)
2. Verify tool description clearly states when to use it
3. Add explicit instruction: "When user asks X, call tool Y"
4. Print registered tools to debug: `print(list(mcp_server.tools.keys()))`

## HTMX not working

**Symptom:** Buttons cause full page reload or nothing happens

**Fix:**
1. Check HTMX script loaded in base template
2. Verify hx-post, hx-target, hx-vals all present
3. hx-vals must be valid JSON: `hx-vals='{"message":"..."}'`
4. hx-target must match element ID: `hx-target="#content"`

## Form data not reaching agent

**Symptom:** Agent doesn't see form field values

**Fix:**
1. Form fields need `name` attribute
2. Hidden message field must exist
3. Verify FastAPI extracts form fields and appends to message

## Blank response

**Symptom:** Empty content area after request

**Fix:**
1. Check agent properly extracts TextBlock content
2. Look for ResultMessage.is_error being True
3. Add logging to see what messages are received
