# ABOUTME: Template for new principle files in knowledge/solutions/principles/
# ABOUTME: Used by the compound-knowledge skill when capturing engineering wisdom

# Principle File Template

Use this template when creating new principle files. Replace placeholders with actual content.

```markdown
---
title: "{Clear principle name}"
project: {project-name or cross-project}
date: {YYYY-MM-DD}
problem_type: principles
component: {enum value from yaml-schema.md}
statement: "{Concise, generalizable rule — 1-2 sentences}"
confidence: {high|medium|low}
solution_summary: "{One-line description of the principle}"
severity: {critical|high|medium|low}
tags: [{keyword1}, {keyword2}, {keyword3}]  # optional
related_solutions:  # optional
  - "{category}/{related-file}.md"
---

## Principle

{The principle statement expanded with context. Why does this matter? What problem does it prevent?}

## Rationale

{Why this principle exists. What experience or evidence led to it? Reference specific projects or incidents.}

## Evidence

{Where this principle has been validated.}

- **{Project 1}**: {How it was confirmed}
- **{Project 2}**: {How it was confirmed}

## Guidelines

{Practical rules for applying this principle.}

- {Guideline 1}
- {Guideline 2}
- {Guideline 3}

## Examples

{Concrete examples of the principle in action.}

### Good Example
{What following the principle looks like}

### Bad Example
{What violating the principle looks like}

## Exceptions

{When this principle does NOT apply, or when it should be relaxed.}

- {Exception 1}: {Why}
- {Exception 2}: {Why}
```

## Guidelines for Using This Template

1. **Statement is key** — future searchers will grep by statement. Make it concise and searchable.
2. **Evidence builds confidence** — more validated projects = higher confidence rating.
3. **Guidelines are actionable** — someone reading this should know exactly what to do.
4. **Exceptions prevent dogma** — every principle has boundaries. Document them.
5. **Cross-reference** — link to related solutions or principles via `related_solutions` frontmatter field.
