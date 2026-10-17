---
title: "A skill's value tracks how specific its knowledge is"
date: 2026-03-20
project: skill-lab
problem_type: principles
component: claude-code
severity: medium
solution_summary: "Skills that encode tool-specific or proprietary knowledge the model can't infer earn their keep; skills that restate general practice add tokens without changing behaviour"
statement: "Tool-specific or proprietary knowledge has the highest skill value: a skill earns its place by teaching what the model can't already infer, such as an API's quirks, a house format, or a team's conventions. General advice the model already follows is cost without effect."
confidence: high
tags:
  - skill-design
  - skill-value
  - knowledge-specificity
  - evals
---

## Statement

Tool-specific or proprietary knowledge has the highest skill value. A skill earns its place by
teaching what the model can't already infer: an API's quirks, a house format, a team's conventions.

## Evidence

Across a dozen skills evaluated with and without their instructions, the skills that encoded API
details (field names, pagination, auth) moved pass rates the most. Skills that restated general
practice ("write clear code", "handle errors") moved them least, often not at all.

## When to Apply

- Deciding whether a new skill is worth writing.
- Choosing what goes in a SKILL.md: spend its lines on the specifics, such as the exact API shape,
  the error the service actually returns, and the format the user's tool expects.

## Anti-Patterns

- A skill that is mostly a generic checklist the model would follow anyway.
- Leaving the tool-specific details to be rediscovered each session.
