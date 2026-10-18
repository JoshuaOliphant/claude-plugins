#!/usr/bin/env bash
# ABOUTME: Setup script for Claude Code cloud environments: installs the plugins sessions here use and the
# ABOUTME: packages Claude Code's Bash sandbox needs. Every step is idempotent and only warns on failure.
#
# Usage, as the environment's setup script (works in any project, since it needs no clone):
#   curl -fsSL https://raw.githubusercontent.com/JoshuaOliphant/claude-plugins/main/scripts/cloud-setup.sh | bash
# Not `bash scripts/cloud-setup.sh`: sessions start in /home/user, above the clone, so that exits 127.
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

# bubblewrap and socat back Claude Code's Bash sandbox on Linux. The skill-mutation harness
# (ai_docs/experiments/skill-mutation) won't run its subject without that sandbox.
ensure_sandbox_deps() {
  command -v bwrap >/dev/null 2>&1 && command -v socat >/dev/null 2>&1 && return 0
  command -v apt-get >/dev/null 2>&1 || { warn "no apt-get; install bubblewrap and socat by hand"; return 0; }
  local sudo=""
  [ "$(id -u)" -eq 0 ] || sudo="sudo"
  # The image's package lists are stale; without the update apt can't find either package.
  { $sudo apt-get update -qq && $sudo apt-get install -y -qq bubblewrap socat; } \
    || warn "could not install bubblewrap and socat"
}

ensure_sandbox_deps

if ! command -v claude >/dev/null 2>&1; then
  warn "claude CLI not found; skipping plugin installs"
  exit 0
fi

ensure_plugin oliphant-plugins JoshuaOliphant/claude-plugins compost
# Source per https://docs.typesafe.ai/agent-skill
ensure_plugin typesafe-ai typesafe-ai/skills typesafe
