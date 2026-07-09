---
name: sdlc-retro
description: Retrospective over archived SDLC runs — mine the run ledger and propose skill improvements as a reviewable PR
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Skill
---

# SDLC Retro

Run the `sdlc-retro` skill: digest the run ledger at `~/.claude/autonomous-sdlc/`,
grade the previous retro, mine the archived traces for cross-run patterns, and
deliver ≤5 grounded improvement proposals (PR in author mode, feedback entries in
consumer mode), then mark the retro.

Do not run this inside an active loop iteration — it is the between-features
feedback step, invoked by the human.
