"""Beads Integration Module - AI Developer Workflow (ADW)

This module provides beads issue management as an alternative to GitHub issues.
Allows ADW workflows to work with local beads tasks for offline development.
"""

import os
import subprocess
import json
from typing import Tuple, Optional
from adw_modules.data_types import GitHubIssue
from datetime import datetime


def get_workspace_root() -> str:
    """Get workspace root for beads operations."""
    # Assume workspace root is the parent of adws directory
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )


def fetch_beads_issue(issue_id: str) -> Tuple[Optional[GitHubIssue], Optional[str]]:
    """Fetch beads issue and convert to GitHubIssue format.

    Args:
        issue_id: The beads issue ID

    Returns:
        Tuple of (GitHubIssue, error_message)
    """
    workspace_root = get_workspace_root()

    # Use bd show to get issue details
    cmd = ["bd", "show", issue_id]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=workspace_root,
        )

        if result.returncode != 0:
            return None, f"Failed to fetch beads issue: {result.stderr}"

        # Parse the output (bd show returns human-readable format)
        # Format is:
        # poc-fjw: Token Infrastructure & Redis Setup
        # Status: in_progress
        # Priority: P0
        # Type: feature
        # ...
        # Description:
        # <description text>
        output = result.stdout

        # Extract title, description, status from output
        title = None
        description = None
        status = "open"
        issue_type = "task"
        in_description = False
        description_lines = []

        for line in output.split("\n"):
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # First line has format: "poc-fjw: Token Infrastructure & Redis Setup"
            if not title and ":" in line and not line.startswith(" "):
                parts = line.split(":", 1)
                if len(parts) == 2 and parts[0].strip() == issue_id:
                    title = parts[1].strip()
                    continue
            
            # Status line
            if stripped.startswith("Status:"):
                status = stripped.split(":", 1)[1].strip()
                in_description = False
            # Type line
            elif stripped.startswith("Type:"):
                issue_type = stripped.split(":", 1)[1].strip()
                in_description = False
            # Description section
            elif stripped.startswith("Description:"):
                in_description = True
                # Check if description is on same line
                desc_text = stripped.split(":", 1)[1].strip()
                if desc_text:
                    description_lines.append(desc_text)
            elif in_description and stripped and not stripped.startswith("Dependents"):
                description_lines.append(stripped)
            elif stripped.startswith("Dependents") or stripped.startswith("Dependencies"):
                in_description = False

        # Combine description lines
        if description_lines:
            description = "\n".join(description_lines)

        if not title:
            return None, "Could not parse issue title from beads output"

        # Convert to GitHubIssue format for compatibility
        # Use the issue_id as the number (extract numeric part if present)
        try:
            # Try to extract number from ID like "poc-123"
            number_str = issue_id.split("-")[-1]
            if number_str.isdigit():
                number = int(number_str)
            else:
                # Use hash of ID as fallback
                number = hash(issue_id) % 10000
        except:
            number = hash(issue_id) % 10000

        # Create GitHubIssue-compatible object
        issue = GitHubIssue(
            number=number,
            title=title or "Untitled Task",
            body=description or "",
            state=status,
            author={"login": "beads"},
            assignees=[],
            labels=[{"name": issue_type}],
            milestone=None,
            comments=[],
            createdAt=datetime.now().isoformat(),
            updatedAt=datetime.now().isoformat(),
            closedAt=None,
            url=f"beads://{issue_id}",
        )

        return issue, None

    except FileNotFoundError:
        return None, "bd command not found. Is beads installed?"
    except Exception as e:
        return None, f"Error fetching beads issue: {str(e)}"


def update_beads_status(issue_id: str, status: str) -> Tuple[bool, Optional[str]]:
    """Update beads issue status.

    Args:
        issue_id: The beads issue ID
        status: New status (open, in_progress, blocked, closed)

    Returns:
        Tuple of (success, error_message)
    """
    workspace_root = get_workspace_root()

    cmd = ["bd", "update", issue_id, "--status", status]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=workspace_root,
        )

        if result.returncode != 0:
            return False, f"Failed to update beads status: {result.stderr}"

        return True, None

    except FileNotFoundError:
        return False, "bd command not found. Is beads installed?"
    except Exception as e:
        return False, f"Error updating beads status: {str(e)}"


def close_beads_issue(issue_id: str, reason: str = "Completed via ADW workflow") -> Tuple[bool, Optional[str]]:
    """Close a beads issue.

    Args:
        issue_id: The beads issue ID
        reason: Reason for closing

    Returns:
        Tuple of (success, error_message)
    """
    workspace_root = get_workspace_root()

    cmd = ["bd", "close", issue_id, "--reason", reason]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=workspace_root,
        )

        if result.returncode != 0:
            return False, f"Failed to close beads issue: {result.stderr}"

        return True, None

    except FileNotFoundError:
        return False, "bd command not found. Is beads installed?"
    except Exception as e:
        return False, f"Error closing beads issue: {str(e)}"


def get_ready_beads_tasks(limit: int = 10) -> Tuple[Optional[list], Optional[str]]:
    """Get ready beads tasks (no blockers).

    Args:
        limit: Maximum number of tasks to return

    Returns:
        Tuple of (task_list, error_message)
    """
    workspace_root = get_workspace_root()

    cmd = ["bd", "ready", "--limit", str(limit)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=workspace_root,
        )

        if result.returncode != 0:
            return None, f"Failed to get ready tasks: {result.stderr}"

        # Parse output to extract task IDs
        # bd ready returns format like:
        # 📋 Ready work (1 issues with no blockers):
        #
        # 1. [P0] poc-pw3: Credit Consumption & Atomicity
        #    Assignee: La Boeuf
        tasks = []
        
        # Check if there are no ready tasks
        if "No ready work found" in result.stdout or "(0 issues" in result.stdout:
            return [], None
        
        for line in result.stdout.split("\n"):
            line = line.strip()
            # Skip empty lines, headers, and assignee lines
            if not line or line.startswith("📋") or line.startswith("Assignee:"):
                continue
            
            # Look for lines with format: "1. [P0] poc-pw3: Title"
            # Extract the task ID (poc-pw3 in this case)
            if ". [P" in line or ". [" in line:
                # Split on ": " to get the ID part
                parts = line.split(":")
                if len(parts) >= 2:
                    # Get the part before the colon, then extract the ID
                    # Format: "1. [P0] poc-pw3"
                    id_part = parts[0].strip()
                    # Split by spaces and get the last token (the ID)
                    tokens = id_part.split()
                    if tokens:
                        task_id = tokens[-1]
                        # Verify it looks like a beads ID (has hyphen)
                        if "-" in task_id:
                            tasks.append(task_id)

        return tasks, None

    except FileNotFoundError:
        return None, "bd command not found. Is beads installed?"
    except Exception as e:
        return None, f"Error getting ready tasks: {str(e)}"


def is_beads_issue(issue_identifier: str) -> bool:
    """Check if an issue identifier is a beads issue.

    Beads issues have format like: poc-abc, feat-123, etc.
    GitHub issues are just numbers.

    Args:
        issue_identifier: The issue identifier

    Returns:
        True if it's a beads issue, False otherwise
    """
    # Beads issues contain a hyphen
    return "-" in issue_identifier and not issue_identifier.isdigit()
