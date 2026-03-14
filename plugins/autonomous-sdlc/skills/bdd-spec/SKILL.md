---
name: bdd-spec
description: >
  This skill should be used when brainstorming features, defining requirements, discussing what
  something should do, writing acceptance criteria, exploring edge cases, or starting new feature
  work before implementation begins. This is the conversational, pre-code phase — defining WHAT to
  build, not building it. Trigger phrases include "what should happen when", "help me spec this out",
  "let's define the requirements", "write acceptance criteria", "BDD", "behavior driven", "what are
  the edge cases", "help me think through this feature", and "define requirements". Not for generating
  test code — use bdd-generate for that.
version: 1.0.0
---

# Acceptance Criteria Co-Author

## Goal

Co-author acceptance criteria with the user before code exists. Produce structured Given/When/Then specs that define *what* "done" means — the source of truth that feeds the SDLC pipeline (architect plans, builder TDD targets, validator reports, bdd-generate scaffolding).

Stance: assume the user is learning BDD. Guide, don't lecture. Ask questions, don't assert assumptions.

## Dependencies

### Tools

- None required — this is a conversational skill that produces markdown output.

### Connectors

- **SDLC pipeline** — Output feeds into: architect (plan documents), builder (TDD targets), validator (PASS/FAIL rows), and `bdd-generate` (Gherkin scaffolding). The handoff to `bdd-generate` is optional.

## Context

### Output Format

```markdown
## Acceptance Criteria: {Feature Name}

### AC-1: {Descriptive title}
**Given** {precondition — state before the action}
**When** {single action the user or system takes}
**Then** {verifiable, measurable outcome}
  and {additional outcome on indented line}

**Edge cases:**
- {What should happen when...?}

**Notes:** {Open questions, V2 considerations, or scope decisions}
```

Design rules:
- **AC-N numbering** — provides traceability from spec → plan → implementation → verification
- **Bold Given/When/Then** — human-readable markdown, not Gherkin. Conversion happens in `bdd-generate`
- **One action per When** — if "When" contains "and", split into separate criteria
- **Verifiable Then** — every outcome must be observable and testable. "The system works correctly" is not verifiable. "The system returns HTTP 200 with `user_id`" is.
- **Scenario Outline tables** — consolidate when 3+ edge cases follow the same pattern:

```markdown
### AC-N: Input validation (parameterized)
**Given** a user on the registration form
**When** the user submits with `<input>`
**Then** the system displays `<error_message>`

| input | error_message |
|-------|---------------|
| empty email | "Email is required" |
| "not-an-email" | "Invalid email format" |
```

### Anti-Patterns

| Anti-Pattern | Example | Fix |
|---|---|---|
| Implementation-as-criteria | "Then the system stores a bcrypt hash" | "Then the password is stored securely" |
| God criterion | AC covers login + session + redirect + audit | Split into AC-1, AC-2, AC-3, AC-4 |
| Missing the Given | "When the user clicks delete Then removed" | "Given a user viewing their own item When..." |
| Non-verifiable Then | "Then handles the error gracefully" | "Then displays 'Unable to process' and logs correlation ID" |

### Positive Patterns

- **Negative Path** — spec what should *not* happen: "Then does not reveal whether the email exists"
- **State Transition** — "Given order in 'pending' When payment confirmed Then transitions to 'confirmed'"
- **Permission Matrix** — Scenario Outline for role-based access (role × action × result table)

### Edge Case Probing

For structured probing questions organized by domain (input validation, auth, state integrity, concurrency, boundaries, errors, external deps, UX states), consult:

→ **`references/edge-case-checklist.md`**

For BDD terminology definitions, consult:

→ **`references/bdd-glossary.md`**

## Process

### Step 1: Understand Feature Intent

Redirect implementation language to behavior language. "I need JWT authentication" → "Users need to log in and stay authenticated across requests."

Ask:
- Who is the actor? (End user, admin, system, external service?)
- What is the core behavior?
- Why does this matter?
- What does success look like from the actor's perspective?

Red flag: if the user describes *how* instead of *what*, gently redirect.

### Step 2: Write the Happy Path

Coach the Given/When/Then for the primary success scenario:
- **Given** — What must be true before the action?
- **When** — What single action triggers the behavior?
- **Then** — What is the observable result?

Write it. Read it back. Ask: "Does this capture what you mean?"

### Step 3: Probe for Error Scenarios

Consult `references/edge-case-checklist.md` for structured probing questions.

Present edge cases as questions, not assertions. Let the user decide what matters for V1:
- "What should happen when the user submits an empty form?"
- "What if the database is unreachable?"
- "What about concurrent updates?"

For each confirmed edge case, write a full AC block or add to an existing AC's edge case list.

### Step 4: Look for Scenario Outlines

When 3+ edge cases follow the same behavioral pattern, consolidate into a parameterized table. Signs: "It should reject empty, too-long, and malformed input" or "Different roles have different permissions."

### Human Checkpoint: Review and Refine

Read back all acceptance criteria, then:

1. **Scope check** — "Are we trying to do too much for V1? What can wait?"
2. **Completeness check** — "Is there a scenario we haven't considered?"
3. **Verifiability check** — "Can each Then be tested automatically?"
4. **One more thing** — "Anything else before we lock these down?"

Mark deferred items with "V2:" prefix in a Notes section.

**Wait for user confirmation before considering the spec complete.**

## Output

Structured acceptance criteria in markdown, ready to:
- Slot into the `## Acceptance Criteria` section of an architect plan document
- Feed into `bdd-generate` for Gherkin scaffolding
- Serve as standalone specification artifacts

AC-N numbers provide traceability across the entire SDLC pipeline.
