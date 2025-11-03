"""
Claude Code SDK - The SDK Way

This module demonstrates the idiomatic way to use the Claude Code Python SDK
for programmatic agent interactions. It focuses on clean, type-safe patterns
using the SDK's native abstractions.

Key Concepts:
- Use `query()` for one-shot operations
- Use `ClaudeSDKClient` for interactive sessions
- Work directly with SDK message types
- Leverage async/await for clean concurrency
- Configure options for your use case

Example Usage:
    # Simple query
    async for message in query(prompt="What is 2 + 2?"):
        if isinstance(message, AssistantMessage):
            print(extract_text(message))
    
    # With options
    options = ClaudeCodeOptions(
        model="claude-sonnet-4-20250514",
        allowed_tools=["Read", "Write"],
        permission_mode="bypassPermissions"
    )
    async for message in query(prompt="Create hello.py", options=options):
        process_message(message)
    
    # Interactive session
    async with create_session() as client:
        await client.query("Debug this error")
        async for msg in client.receive_response():
            handle_message(msg)
"""

import logging
from pathlib import Path
from typing import AsyncIterator, Optional, List
from contextlib import asynccontextmanager

# Import all SDK components we'll use
from claude_code_sdk import (
    # Main functions
    query,
    ClaudeSDKClient,
    
    # Configuration
    ClaudeCodeOptions,
    PermissionMode,
    
    # Message types
    Message,
    AssistantMessage,
    UserMessage,
    SystemMessage,
    ResultMessage,
    
    # Content blocks
    ContentBlock,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    
    # Errors
    ClaudeSDKError,
    CLIConnectionError,
    CLINotFoundError,
    ProcessError,
)

# Set up logging
logger = logging.getLogger(__name__)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_text(message: AssistantMessage) -> str:
    """Extract all text content from an assistant message.
    
    The SDK way: Work directly with typed message objects.
    
    Args:
        message: AssistantMessage with content blocks
        
    Returns:
        Concatenated text from all text blocks
    """
    texts = []
    for block in message.content:
        if isinstance(block, TextBlock):
            texts.append(block.text)
    return "\n".join(texts)


def extract_tool_uses(message: AssistantMessage) -> List[ToolUseBlock]:
    """Extract all tool use blocks from an assistant message.
    
    Args:
        message: AssistantMessage with content blocks
        
    Returns:
        List of ToolUseBlock objects
    """
    return [
        block for block in message.content 
        if isinstance(block, ToolUseBlock)
    ]


def get_result_text(messages: List[Message]) -> str:
    """Extract final result text from a list of messages.
    
    Args:
        messages: List of messages from a query
        
    Returns:
        Result text or assistant responses
    """
    # First check for ResultMessage
    for msg in reversed(messages):
        if isinstance(msg, ResultMessage) and msg.result:
            return msg.result
    
    # Otherwise collect assistant text
    texts = []
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            text = extract_text(msg)
            if text:
                texts.append(text)
    
    return "\n".join(texts)


# ============================================================================
# ONE-SHOT QUERIES (The Simple SDK Way)
# ============================================================================

async def simple_query(prompt: str, model: str = "claude-sonnet-4-5-20250929") -> str:
    """Simple one-shot query with text response.
    
    The SDK way: Direct use of query() with minimal setup.
    
    Args:
        prompt: What to ask Claude
        model: Which model to use
        
    Returns:
        Text response from Claude
        
    Example:
        response = await simple_query("What is 2 + 2?")
        print(response)  # "4" or "2 + 2 equals 4"
    """
    options = ClaudeCodeOptions(model=model)
    
    texts = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            text = extract_text(message)
            if text:
                texts.append(text)
    
    return "\n".join(texts) if texts else "No response"


async def query_with_tools(
    prompt: str,
    allowed_tools: List[str],
    working_dir: Optional[Path] = None
) -> AsyncIterator[Message]:
    """Query with specific tools enabled.
    
    The SDK way: Configure options for your use case.
    
    Args:
        prompt: What to ask Claude
        allowed_tools: List of tool names to allow
        working_dir: Optional working directory
        
    Yields:
        SDK message objects
        
    Example:
        async for msg in query_with_tools(
            "Create a Python script",
            allowed_tools=["Write", "Read"]
        ):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        print(f"Using tool: {block.name}")
    """
    options = ClaudeCodeOptions(
        allowed_tools=allowed_tools,
        cwd=str(working_dir) if working_dir else None,
        permission_mode="bypassPermissions"  # For automated workflows
    )
    
    async for message in query(prompt=prompt, options=options):
        yield message


async def collect_query_response(
    prompt: str,
    options: Optional[ClaudeCodeOptions] = None
) -> tuple[List[Message], Optional[ResultMessage]]:
    """Collect all messages from a query.
    
    The SDK way: Async iteration with type checking.
    
    Args:
        prompt: What to ask Claude
        options: Optional configuration
        
    Returns:
        Tuple of (all_messages, result_message)
        
    Example:
        messages, result = await collect_query_response("List files")
        if result and not result.is_error:
            print("Success!")
        for msg in messages:
            process_message(msg)
    """
    if options is None:
        options = ClaudeCodeOptions()
    
    messages = []
    result = None
    
    async for message in query(prompt=prompt, options=options):
        messages.append(message)
        if isinstance(message, ResultMessage):
            result = message
    
    return messages, result


# ============================================================================
# INTERACTIVE SESSIONS (The SDK Client Way)
# ============================================================================

@asynccontextmanager
async def create_session(
    model: str = "claude-sonnet-4-5-20250929",
    working_dir: Optional[Path] = None
):
    """Create an interactive session with Claude.
    
    The SDK way: Use context managers for resource management.
    
    Args:
        model: Which model to use
        working_dir: Optional working directory
        
    Yields:
        Connected ClaudeSDKClient
        
    Example:
        async with create_session() as client:
            await client.query("Hello")
            async for msg in client.receive_response():
                print(msg)
    """
    options = ClaudeCodeOptions(
        model=model,
        cwd=str(working_dir) if working_dir else None,
        permission_mode="bypassPermissions"
    )
    
    client = ClaudeSDKClient(options=options)
    await client.connect()
    
    try:
        yield client
    finally:
        await client.disconnect()


async def interactive_conversation(prompts: List[str]) -> List[Message]:
    """Have an interactive conversation with Claude.
    
    The SDK way: Bidirectional communication with the client.
    
    Args:
        prompts: List of prompts to send in sequence
        
    Returns:
        All messages from the conversation
        
    Example:
        messages = await interactive_conversation([
            "What's the weather like?",
            "Tell me more about clouds",
            "How do they form?"
        ])
    """
    all_messages = []
    
    async with create_session() as client:
        for prompt in prompts:
            # Send prompt
            await client.query(prompt)
            
            # Collect response
            async for msg in client.receive_response():
                all_messages.append(msg)
                if isinstance(msg, ResultMessage):
                    break
    
    return all_messages


# ============================================================================
# ERROR HANDLING (The SDK Way)
# ============================================================================

async def safe_query(prompt: str) -> tuple[Optional[str], Optional[str]]:
    """Query with comprehensive error handling.
    
    The SDK way: Handle specific SDK exceptions.
    
    Args:
        prompt: What to ask Claude
        
    Returns:
        Tuple of (response_text, error_message)
        
    Example:
        response, error = await safe_query("Help me debug this")
        if error:
            print(f"Error: {error}")
        else:
            print(f"Response: {response}")
    """
    try:
        response = await simple_query(prompt)
        return response, None
        
    except CLINotFoundError:
        return None, "Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
        
    except CLIConnectionError as e:
        return None, f"Connection error: {str(e)}"
        
    except ProcessError as e:
        return None, f"Process error (exit code {e.exit_code}): {str(e)}"
        
    except ClaudeSDKError as e:
        return None, f"SDK error: {str(e)}"
        
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


# ============================================================================
# ADVANCED PATTERNS (The SDK Way)
# ============================================================================

async def stream_with_progress(
    prompt: str,
    on_text: Optional[callable] = None,
    on_tool: Optional[callable] = None
) -> ResultMessage:
    """Stream query with progress callbacks.
    
    The SDK way: Process messages as they arrive.
    
    Args:
        prompt: What to ask Claude
        on_text: Callback for text blocks (optional)
        on_tool: Callback for tool use blocks (optional)
        
    Returns:
        Final ResultMessage
        
    Example:
        result = await stream_with_progress(
            "Analyze this codebase",
            on_text=lambda text: print(f"Claude: {text}"),
            on_tool=lambda tool: print(f"Using: {tool.name}")
        )
        print(f"Cost: ${result.total_cost_usd:.4f}")
    """
    result = None
    
    async for message in query(prompt=prompt):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock) and on_text:
                    on_text(block.text)
                elif isinstance(block, ToolUseBlock) and on_tool:
                    on_tool(block)
        
        elif isinstance(message, ResultMessage):
            result = message
    
    return result


async def query_with_timeout(prompt: str, timeout_seconds: float = 30) -> Optional[str]:
    """Query with timeout protection.
    
    The SDK way: Use asyncio for timeout control.
    
    Args:
        prompt: What to ask Claude
        timeout_seconds: Maximum time to wait
        
    Returns:
        Response text or None if timeout
        
    Example:
        response = await query_with_timeout("Complex analysis", timeout_seconds=60)
        if response is None:
            print("Query timed out")
    """
    import asyncio
    
    try:
        # Create the query task
        async def _query():
            return await simple_query(prompt)
        
        # Run with timeout
        response = await asyncio.wait_for(_query(), timeout=timeout_seconds)
        return response
        
    except asyncio.TimeoutError:
        logger.warning(f"Query timed out after {timeout_seconds} seconds")
        return None

