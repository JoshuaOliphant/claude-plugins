# ABOUTME: Utility functions for ADW modules
# ABOUTME: Common helpers for parsing, formatting, and data transformation

import json
from typing import Any, Optional


def parse_json(json_str: str, default: Optional[Any] = None) -> Any:
    """Parse JSON string safely with fallback to default value.

    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON object or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError, ValueError):
        return default
