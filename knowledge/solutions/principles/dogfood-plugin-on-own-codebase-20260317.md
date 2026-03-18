---
title: "Dogfood your plugin on its own codebase"
date: 2026-03-17
project: cross-project
problem_type: principles
component: claude-code-plugins
severity: medium
solution_summary: "Test plugin patterns by using the plugin itself to do work on its own codebase — reveals integration gaps, UX issues, and incorrect assumptions faster than synthetic tests"
statement: "The best test of an orchestration plugin is to use it to orchestrate work on its own codebase. Dogfooding reveals integration gaps, incorrect assumptions, and UX issues that synthetic evals miss."
confidence: high
tags:
  - dogfooding
  - plugin-testing
  - integration-testing
  - autonomous-sdlc
related_solutions:
  - "workflow/parallel-worktree-builders-claude-plugins-20260317.md"
  - "patterns/plugin-modernization-claude-code-v2-claude-plugins-20260316.md"
---

## Statement

The best test of an orchestration plugin is to use it to orchestrate work on its own codebase. Dogfooding reveals integration gaps, incorrect assumptions, and UX issues that synthetic evals miss.

## Evidence

Used the autonomous-sdlc plugin (v0.9.0) to implement its own remaining modernization tasks:
- 5 parallel builders dispatched with `isolation: "worktree"`
- Each builder worked on a separate improvement to the plugin itself
- Discovered that worktree isolation behavior varies by task complexity (4/5 committed directly to main)
- Discovered spillover where a worktree builder wrote to both worktree and main working directory
- The stop hook, spawn restrictions, and wave transition hooks were all validated by being part of the codebase being modified

## When to Apply

- After building or significantly modifying a Claude Code plugin
- Before publishing a new version — use the plugin to do real work first
- When writing eval prompts — consider whether a dogfooding scenario would be more revealing than synthetic test cases

## Anti-Patterns

- Testing only with synthetic prompts that don't exercise the full workflow
- Publishing a plugin version without ever using it yourself on real tasks
- Relying solely on unit-level skill evals (with_skill vs without_skill) without end-to-end validation

## Caveats

- Dogfooding a plugin on its own codebase biases toward the types of changes plugins need (frontmatter, markdown, config). Test on an application codebase too for full coverage.
- Self-referential changes can be confusing to review — "did the builder modify its own agent definition correctly?"
