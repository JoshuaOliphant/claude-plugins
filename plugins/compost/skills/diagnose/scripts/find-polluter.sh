#!/usr/bin/env bash
# ABOUTME: Runs test files one at a time and stops at the first one that creates a given path.
# ABOUTME: Finds the test that pollutes shared state, for any test runner.

set -uo pipefail

if [ $# -lt 3 ]; then
  echo "Usage: $0 <path-that-appears> <test-command> <test-file>..." >&2
  echo "Example: $0 .git 'uv run pytest' tests/test_*.py" >&2
  exit 2
fi

pollution="$1"
test_command="$2"
shift 2

if [ -e "$pollution" ]; then
  echo "$pollution already exists; remove it before searching." >&2
  exit 2
fi

total=$#
count=0
for test_file in "$@"; do
  count=$((count + 1))
  echo "[$count/$total] $test_file"
  $test_command "$test_file" > /dev/null 2>&1

  if [ -e "$pollution" ]; then
    echo
    echo "Polluter: $test_file created $pollution"
    ls -la "$pollution"
    exit 1
  fi
done

echo
echo "No test file created $pollution."
