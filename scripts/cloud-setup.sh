#!/usr/bin/env bash
# ABOUTME: Setup script for Claude Code cloud environments: installs the plugins sessions here use.
# ABOUTME: The environment's own setup script runs this; every step is idempotent and only warns on failure.
#
# Usage: bash scripts/cloud-setup.sh
#   TYPESAFE_MARKETPLACE_SOURCE  where to add the typesafe-ai marketplace from (owner/repo or URL);
#                                needed only the first time, before typesafe-ai is registered.
set -uo pipefail

warn() { echo "cloud-setup: warn: $*" >&2; }

has_marketplace() {
  claude plugin marketplace list 2>/dev/null | grep -qE "^[[:space:]]*>?[[:space:]]*$1\$"
}

# Register a marketplace if missing, refresh it, then update the plugin, installing it if update fails.
ensure_plugin() {
  local marketplace="$1" source="$2" plugin="$3"
  if ! has_marketplace "$marketplace"; then
    if [[ -z "$source" ]]; then
      warn "no source for marketplace $marketplace; skipping $plugin@$marketplace"
      return 0
    fi
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
ensure_plugin typesafe-ai "${TYPESAFE_MARKETPLACE_SOURCE:-}" typesafe
