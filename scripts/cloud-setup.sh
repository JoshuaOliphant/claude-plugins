#!/usr/bin/env bash
# ABOUTME: Setup script for Claude Code cloud environments: installs the plugins sessions here use.
# ABOUTME: The environment's own setup script runs this; every step is idempotent and only warns on failure.
#
# Usage: bash /home/user/claude-plugins/scripts/cloud-setup.sh
# Cloud sessions start in /home/user, one level above the clone, so the environment's setup
# script must use this absolute path; `bash scripts/cloud-setup.sh` exits 127 there.
set -uo pipefail

warn() { echo "cloud-setup: warn: $*" >&2; }

has_marketplace() {
  claude plugin marketplace list 2>/dev/null | grep -qE "^[[:space:]]*>?[[:space:]]*$1\$"
}

# Register a marketplace if missing, refresh it, then update the plugin, installing it if update fails.
ensure_plugin() {
  local marketplace="$1" source="$2" plugin="$3"
  if ! has_marketplace "$marketplace"; then
    claude plugin marketplace add "$source" || { warn "could not add marketplace $source"; return 0; }
  fi
  claude plugin marketplace update "$marketplace" || warn "marketplace update $marketplace failed"
  claude plugin update "$plugin@$marketplace" 2>/dev/null \
    || claude plugin install "$plugin@$marketplace" \
    || warn "could not install $plugin@$marketplace"
}

if ! command -v claude >/dev/null 2>&1; then
  warn "claude CLI not found; skipping plugin installs"
  exit 0
fi

ensure_plugin oliphant-plugins JoshuaOliphant/claude-plugins compost
# Source per https://docs.typesafe.ai/agent-skill
ensure_plugin typesafe-ai typesafe-ai/skills typesafe
