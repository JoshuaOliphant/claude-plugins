#!/bin/bash
# ABOUTME: Auto-approve hook for autonomous SDLC workflows
# ABOUTME: Returns allow decision when .sdlc marker exists

# Check if we're in an SDLC workflow (marker file exists)
if [ -d ".sdlc" ] || [ -f ".sdlc-active" ]; then
    # Auto-approve all permission requests during SDLC workflow
    echo '{"decision": "allow"}'
else
    # Not in SDLC workflow - defer to default behavior
    echo '{}'
fi
