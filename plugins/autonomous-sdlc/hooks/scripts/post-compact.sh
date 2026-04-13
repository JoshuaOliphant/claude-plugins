#!/bin/bash
# ABOUTME: PostCompact hook for autonomous SDLC workflows
# ABOUTME: Re-surfaces in-progress beads after context compaction to prevent lost work context

# Only inject context if beads CLI is available
if ! which bd &>/dev/null; then
    exit 0
fi

# Only act if we're in an SDLC workflow
if [ ! -d ".sdlc" ] && [ ! -f ".sdlc-active" ]; then
    exit 0
fi

# Get in-progress beads
IN_PROGRESS=$(bd list --status=in_progress 2>/dev/null)
if [ -z "$IN_PROGRESS" ]; then
    exit 0
fi

# Inject as system message so agents know what was in flight
printf '{"systemMessage": "[PostCompact] Context was compacted. In-progress beads at time of compaction:\n%s"}\n' "$IN_PROGRESS"
