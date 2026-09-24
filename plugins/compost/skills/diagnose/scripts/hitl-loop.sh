#!/usr/bin/env bash
# ABOUTME: Template for a reproduction loop that a person drives by following prompts.
# ABOUTME: Copy it, edit the steps, run it; captured answers print as KEY=VALUE for the agent to read.

set -euo pipefail

step() {
  printf '\n>>> %s\n' "$1"
  read -r -p "    [Enter when done] " _
}

capture() {
  local var="$1" question="$2" answer
  printf '\n>>> %s\n' "$question"
  read -r -p "    > " answer
  printf -v "$var" '%s' "$answer"
}

# `capture` echoes answers back to the terminal where the agent reads them, so use it for
# observations and leave signing in to the person as a `step`.

step "Open the app at http://localhost:3000 and sign in."

capture ERRORED "Click the 'Export' button. Did it throw an error? (y/n)"

capture ERROR_MSG "Paste the error message (or 'none'):"

printf '\n--- Captured ---\n'
printf 'ERRORED=%s\n' "$ERRORED"
printf 'ERROR_MSG=%s\n' "$ERROR_MSG"
