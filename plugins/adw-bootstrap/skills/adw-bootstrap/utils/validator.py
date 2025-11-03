#!/usr/bin/env python3
"""
Validation utilities for ADW setup.

Simple checks to ensure ADW infrastructure is correctly installed and functional.
These are mechanical validations that don't require AI reasoning.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def check_claude_installed() -> Tuple[bool, str]:
    """Check if Claude Code CLI is available.

    Returns:
        Tuple of (success, message)
    """
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            version = result.stdout.strip()
            return (True, f"✓ Claude Code CLI installed: {version}")
        else:
            return (False, "✗ Claude Code CLI not responding correctly")

    except FileNotFoundError:
        return (False, "✗ Claude Code CLI not found. Install from: https://claude.ai/code")
    except subprocess.TimeoutExpired:
        return (False, "✗ Claude Code CLI timeout")
    except Exception as e:
        return (False, f"✗ Error checking Claude Code: {e}")


def check_api_key_configured() -> Tuple[bool, str]:
    """Check if ANTHROPIC_API_KEY is configured (optional).

    Returns:
        Tuple of (configured, message)
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if api_key:
        # Mask the key for display
        masked = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
        return (True, f"✓ API key configured: {masked}")
    else:
        return (False, "ℹ No API key (using subscription mode)")


def validate_directory_structure(project_root: str) -> List[str]:
    """Check that expected ADW directories exist.

    Args:
        project_root: Path to project root

    Returns:
        List of validation messages
    """
    project_path = Path(project_root)
    messages = []

    # Required directories
    required_dirs = [
        "adws",
        "adws/adw_modules",
        ".claude/commands",
        "specs"
    ]

    for dir_path in required_dirs:
        full_path = project_path / dir_path
        if full_path.exists() and full_path.is_dir():
            messages.append(f"✓ Directory exists: {dir_path}")
        else:
            messages.append(f"✗ Directory missing: {dir_path}")

    # Optional but expected directories
    optional_dirs = [
        "agents",
    ]

    for dir_path in optional_dirs:
        full_path = project_path / dir_path
        if full_path.exists() and full_path.is_dir():
            messages.append(f"✓ Directory exists: {dir_path}")
        else:
            messages.append(f"ℹ Directory not created yet: {dir_path} (will be created on first run)")

    return messages


def validate_core_files(project_root: str) -> List[str]:
    """Check that core ADW files exist.

    Args:
        project_root: Path to project root

    Returns:
        List of validation messages
    """
    project_path = Path(project_root)
    messages = []

    # Core files for minimal setup
    core_files = [
        "adws/adw_modules/agent.py",
        "adws/adw_prompt.py",
        ".claude/commands/chore.md",
        ".claude/commands/implement.md",
    ]

    for file_path in core_files:
        full_path = project_path / file_path
        if full_path.exists() and full_path.is_file():
            messages.append(f"✓ File exists: {file_path}")
        else:
            messages.append(f"✗ File missing: {file_path}")

    # Enhanced setup files (optional)
    enhanced_files = [
        "adws/adw_modules/agent_sdk.py",
        "adws/adw_slash_command.py",
        "adws/adw_chore_implement.py",
        ".claude/commands/feature.md",
    ]

    enhanced_count = sum(1 for f in enhanced_files if (project_path / f).exists())
    if enhanced_count > 0:
        messages.append(f"ℹ Enhanced setup detected ({enhanced_count}/{len(enhanced_files)} files)")
        for file_path in enhanced_files:
            full_path = project_path / file_path
            if full_path.exists() and full_path.is_file():
                messages.append(f"  ✓ {file_path}")

    return messages


def check_scripts_executable(project_root: str) -> List[str]:
    """Verify ADW scripts have execute permissions.

    Args:
        project_root: Path to project root

    Returns:
        List of validation messages
    """
    project_path = Path(project_root)
    messages = []

    # Find all adw_*.py scripts
    adws_dir = project_path / "adws"
    if not adws_dir.exists():
        return ["✗ adws/ directory not found"]

    scripts = list(adws_dir.glob("adw_*.py"))

    if not scripts:
        messages.append("ℹ No ADW scripts found (adw_*.py)")
        return messages

    for script in scripts:
        is_executable = os.access(script, os.X_OK)
        if is_executable:
            messages.append(f"✓ Executable: {script.name}")
        else:
            messages.append(f"⚠ Not executable: {script.name} (run: chmod +x {script})")

    return messages


def test_prompt_execution(project_root: str, timeout: int = 30) -> Tuple[bool, str]:
    """Try a simple prompt execution to verify setup works.

    Args:
        project_root: Path to project root
        timeout: Maximum seconds to wait

    Returns:
        Tuple of (success, message)
    """
    project_path = Path(project_root)
    prompt_script = project_path / "adws" / "adw_prompt.py"

    if not prompt_script.exists():
        return (False, "✗ adw_prompt.py not found")

    try:
        # Simple test prompt
        result = subprocess.run(
            [str(prompt_script), "What is 2 + 2?"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode == 0:
            return (True, "✓ Test prompt executed successfully")
        else:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            return (False, f"✗ Test prompt failed: {error_msg}")

    except subprocess.TimeoutExpired:
        return (False, f"✗ Test prompt timeout (>{timeout}s)")
    except Exception as e:
        return (False, f"✗ Error executing test prompt: {e}")


def validate_output_structure(project_root: str) -> List[str]:
    """Check if output directories are created correctly after execution.

    Args:
        project_root: Path to project root

    Returns:
        List of validation messages
    """
    project_path = Path(project_root)
    agents_dir = project_path / "agents"

    if not agents_dir.exists():
        return ["ℹ No agents/ directory yet (created on first execution)"]

    messages = [f"✓ Output directory exists: agents/"]

    # Check for any execution directories
    execution_dirs = [d for d in agents_dir.iterdir() if d.is_dir()]

    if not execution_dirs:
        messages.append("ℹ No execution outputs yet")
        return messages

    messages.append(f"ℹ Found {len(execution_dirs)} execution output(s)")

    # Check structure of first execution
    first_exec = execution_dirs[0]
    agent_dirs = [d for d in first_exec.iterdir() if d.is_dir()]

    if agent_dirs:
        first_agent = agent_dirs[0]
        expected_files = [
            "cc_raw_output.jsonl",
            "cc_raw_output.json",
            "cc_final_object.json",
            "custom_summary_output.json"
        ]

        for filename in expected_files:
            if (first_agent / filename).exists():
                messages.append(f"  ✓ Output file: {filename}")
            else:
                messages.append(f"  ⚠ Missing output: {filename}")

    return messages


def run_full_validation(project_root: str = ".", verbose: bool = True) -> bool:
    """Run complete validation suite.

    Args:
        project_root: Path to project root
        verbose: Print detailed messages

    Returns:
        True if all critical checks pass
    """
    project_root = os.path.abspath(project_root)

    if verbose:
        print(f"\n{'='*60}")
        print(f"ADW Setup Validation")
        print(f"{'='*60}")
        print(f"Project: {project_root}\n")

    all_passed = True

    # Check 1: Claude Code CLI
    if verbose:
        print("1. Claude Code CLI")
        print("-" * 60)

    success, msg = check_claude_installed()
    if verbose:
        print(f"   {msg}")
    if not success:
        all_passed = False

    # Check 2: API Key (optional)
    if verbose:
        print("\n2. API Configuration")
        print("-" * 60)

    configured, msg = check_api_key_configured()
    if verbose:
        print(f"   {msg}")

    # Check 3: Directory structure
    if verbose:
        print("\n3. Directory Structure")
        print("-" * 60)

    dir_messages = validate_directory_structure(project_root)
    for msg in dir_messages:
        if verbose:
            print(f"   {msg}")
        if msg.startswith("✗"):
            all_passed = False

    # Check 4: Core files
    if verbose:
        print("\n4. Core Files")
        print("-" * 60)

    file_messages = validate_core_files(project_root)
    for msg in file_messages:
        if verbose:
            print(f"   {msg}")
        if msg.startswith("✗"):
            all_passed = False

    # Check 5: Script permissions
    if verbose:
        print("\n5. Script Permissions")
        print("-" * 60)

    perm_messages = check_scripts_executable(project_root)
    for msg in perm_messages:
        if verbose:
            print(f"   {msg}")
        if msg.startswith("⚠"):
            # Warning but not critical failure
            pass

    # Check 6: Output structure (informational)
    if verbose:
        print("\n6. Output Structure")
        print("-" * 60)

    output_messages = validate_output_structure(project_root)
    for msg in output_messages:
        if verbose:
            print(f"   {msg}")

    # Summary
    if verbose:
        print(f"\n{'='*60}")
        if all_passed:
            print("✓ Validation passed - ADW setup is ready!")
        else:
            print("✗ Validation failed - see errors above")
        print(f"{'='*60}\n")

    return all_passed


def main():
    """CLI entry point for validation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate ADW setup",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "project_root",
        nargs="?",
        default=".",
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show summary"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run test prompt execution (may take 30s)"
    )

    args = parser.parse_args()

    # Run validation
    passed = run_full_validation(args.project_root, verbose=not args.quiet)

    # Optionally test execution
    if args.test and passed:
        print("\nRunning test prompt execution...")
        print("-" * 60)
        success, msg = test_prompt_execution(args.project_root)
        print(f"   {msg}")
        if not success:
            passed = False

    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
