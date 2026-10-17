---
title: "One feedback manager, parameterized by plugin name, for every plugin's stored preferences"
date: 2026-03-18
project: claude-plugins
problem_type: patterns
component: claude-code
severity: medium
solution_summary: "Persist preferences with one shared feedback_manager.py that takes the plugin name as its first argument; each plugin's feedback skill owns the categories and each consuming skill reads them before acting"
symptoms:
  - "Each new plugin copies and edits its own feedback-storage script"
  - "Preference files land in different places and formats per plugin"
  - "Skills forget user corrections between sessions"
root_cause: logic_error
resolution_type: refactor
tags:
  - feedback
  - persistence
  - preferences
  - plugin-architecture
  - feedback-manager
---

## Problem

Three plugins (mochi-creator, hexagonal-agents, compound-knowledge) each needed to remember user
corrections between sessions. Each grew its own storage script, and the copies drifted.

## Root Cause

Storage, the meaning of a preference, and the point where a skill reads it were all written
together in each plugin, so nothing could be shared.

## Solution

Split feedback persistence into three layers:

1. **Storage.** One `feedback_manager.py`, parameterized by plugin name:
   `python feedback_manager.py <plugin-name> save-feedback '<json>'`, `show-feedback`, and
   `clear-feedback`. Entries are YAML in `~/.claude/<plugin-name>/feedback.yaml`. The script is
   identical in every plugin; the canonical copy lives in `scripts/shared/` and is synced out.
2. **Semantics.** Each plugin's `feedback` skill defines the categories that plugin cares about
   (for example `retrieval_depth` for compound-knowledge) and when to save one.
3. **Consumption.** Every skill that should honour preferences runs `show-feedback` for its plugin
   before it acts, and applies the categories it understands.

A new plugin gets persistence by syncing the shared script in, writing a `feedback` skill for its
categories, and adding the `show-feedback` call to the skills that consume them.

## Prevention

Never fork the storage script for one plugin. Add a category in that plugin's `feedback` skill.
