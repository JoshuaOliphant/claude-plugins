#!/usr/bin/env bash
# ABOUTME: Runs test files one at a time and stops at the first one that creates a given path.
# ABOUTME: Finds the test that pollutes shared state, for any test runner.

set -uo pipefail

usage() {
  echo "Usage: $0 <path-that-appears> <test-command> <test-file>..." >&2
  echo "Example: $0 stray-output.db 'uv run pytest' tests/test_*.py" >&2
  echo "Exit status: 0 polluter found, 1 none found, 2 usage error, 3 test command missing or not executable." >&2
  echo "Each run's stderr goes to a temp log, named on any non-zero exit." >&2
}

if [ $# -lt 3 ]; then
  usage
  exit 2
fi

pollution="$1"
test_command="$2"
shift 2

if [ -e "$pollution" ]; then
  echo "$pollution already exists; remove it before searching." >&2
  exit 2
fi

tmp_root="${TMPDIR:-/tmp}"
stderr_log="$(mktemp "${tmp_root%/}/find-polluter.XXXXXX")"
total=$#
count=0
for test_file in "$@"; do
  count=$((count + 1))
  echo "[$count/$total] $test_file"
  echo "=== [$count/$total] $test_file" >> "$stderr_log"
  $test_command "$test_file" > /dev/null 2>> "$stderr_log"
  status=$?

  if [ "$status" -eq 126 ] || [ "$status" -eq 127 ]; then
    echo "'$test_command' exited $status: the runner is missing or not executable. Stopping." >&2
    echo "stderr: $stderr_log" >&2
    exit 3
  fi
  if [ "$status" -ne 0 ]; then
    echo "[$count/$total] $test_file exited $status (stderr: $stderr_log)"
  fi

  if [ -e "$pollution" ]; then
    echo
    echo "Polluter: $test_file created $pollution"
    ls -la "$pollution"
    exit 0
  fi
done

echo
echo "No test file created $pollution."
exit 1
