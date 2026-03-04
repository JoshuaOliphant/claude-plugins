---
name: bdd-spec
description: This skill should be used when brainstorming features, defining requirements, discussing what something should do, writing acceptance criteria, exploring edge cases, or starting new feature work before implementation begins. Trigger phrases include "what should happen when", "help me spec this out", "BDD", "behavior driven", "acceptance tests", "Given When Then", "acceptance criteria", and "define requirements".
version: 1.0.0
---

# Acceptance Criteria Co-Author

Co-author acceptance criteria with the human before code exists. Specs are the primary control surface — they define *what*, agents figure out *how*. Verification is deterministic and decoupled from the author.

This skill coaches humans through the Given/When/Then format, probes for edge cases, and produces structured acceptance criteria that feed directly into the SDLC pipeline. The output becomes the source of truth for what "done" means.

Stance: assume the human is learning BDD. Guide, don't lecture. Ask questions, don't assert assumptions.

## Quick Start

Starting point — a vague idea:

> "I want users to be able to reset their password"

Clarifying questions to ask:

1. How does the user prove identity? (Email link, security questions, SMS?)
2. What happens if the reset link expires?
3. Should there be rate limiting on reset requests?

Resulting acceptance criteria:

```markdown
## Acceptance Criteria: Password Reset

### AC-1: Successful password reset via email
**Given** a registered user with a verified email address
**When** the user requests a password reset
**Then** a reset link is sent to their registered email
  and the link expires after 30 minutes
  and the link is single-use

### AC-2: Reset with expired link
**Given** a user with an expired password reset link
**When** the user clicks the expired link
**Then** the system displays "This link has expired"
  and offers a "Request new link" action

### AC-3: Rate limiting on reset requests
**Given** a user who has requested 3 password resets in the last hour
**When** the user requests another reset
**Then** the system responds with "Too many requests, try again later"
  and no additional email is sent

**Edge cases:**
- User requests reset for unregistered email (silent success — no information leakage)
- User changes email while a reset link is active (invalidate existing links)
```

## Output Format

Structure all acceptance criteria using this format:

```markdown
## Acceptance Criteria: {Feature Name}

### AC-1: {Descriptive title}
**Given** {precondition — state before the action}
**When** {single action the user or system takes}
**Then** {verifiable, measurable outcome}
  and {additional outcome on indented line}
  and {additional outcome on indented line}

**Edge cases:**
- {What should happen when...?}

**Notes:** {Open questions, V2 considerations, or scope decisions}
```

Design points:

- **AC-N numbering** maps directly to the architect plan template and validator report rows. Numbering provides traceability from spec through implementation to verification.
- **Bold Given/When/Then** — human-readable markdown, not Gherkin syntax. Conversion to Gherkin happens downstream in `bdd-generate`.
- **One action per When** — if "When" contains "and", split into separate criteria.
- **Verifiable Then** — every outcome must be observable and testable. "The system works correctly" is not verifiable. "The system returns HTTP 200 with a JSON body containing `user_id`" is.
- **Multi-line Then** — use `and` continuations on indented lines for compound outcomes.
- **Scenario Outline tables** — when 3+ edge cases follow the same pattern, consolidate:

```markdown
### AC-4: Input validation (parameterized)
**Given** a user on the registration form
**When** the user submits with `<input>`
**Then** the system displays `<error_message>`

| input | error_message |
|-------|---------------|
| empty email | "Email is required" |
| "not-an-email" | "Invalid email format" |
| email longer than 254 chars | "Email is too long" |
```

## Coaching Workflow

### Step 1: Understand feature intent

Redirect implementation language to behavior language. The human might say "I need JWT authentication" — translate to "Users need to log in and stay authenticated across requests."

Questions to ask:
- Who is the actor? (End user, admin, system, external service?)
- What is the core behavior? (What does the actor want to accomplish?)
- Why does this matter? (What problem does this solve?)
- What does success look like from the actor's perspective?

Red flag: if the human describes *how* instead of *what*, gently redirect. "That sounds like an implementation approach. What behavior should the user see?"

### Step 2: Identify the happy path

Coach the Given/When/Then for the primary success scenario:

- **Given** — What must be true before the action? What state is the system in? What has the user already done?
- **When** — What single action triggers the behavior? Keep it atomic. If there are multiple actions, that's multiple criteria.
- **Then** — What is the observable result? Measurable, specific, testable. Not "the system handles it" but "the system returns a 201 with the created resource."

Write the happy path criterion first. Read it back. Ask: "Does this capture what you mean?"

### Step 3: Probe for error scenarios

Consult `references/edge-case-checklist.md` for structured probing questions organized by domain (input validation, auth, state integrity, concurrency, boundaries, errors, external deps, UX states).

Present edge cases as questions, not assertions. Let the human decide what matters for V1:

- "What should happen when the user submits an empty form?"
- "What if the database is unreachable during this operation?"
- "What about concurrent updates to the same resource?"

For each edge case the human confirms matters:
1. Write it as a full AC block (Given/When/Then)
2. Or add it to the Edge Cases list under an existing AC

### Step 4: Look for Scenario Outlines

When 3+ edge cases follow the same behavioral pattern (same Given/When structure, different inputs/outputs), consolidate into a parameterized table.

Signs a Scenario Outline is needed:
- "It should reject empty, too-long, and malformed input"
- "Different roles have different permissions"
- "Various HTTP methods should return specific status codes"

Convert repetitive criteria into the table format shown in the Output Format section.

### Step 5: Review and refine

Read back all acceptance criteria. Then:

1. **Scope check** — "Are we trying to do too much for V1? What can wait?"
2. **Completeness check** — "Is there a scenario we haven't considered?"
3. **Verifiability check** — "Can each Then be tested automatically?"
4. **One more thing** — "Anything else before we lock these down?"

Mark any deferred items in a **Notes** section with "V2:" prefix.

## Patterns and Anti-Patterns

### Anti-Patterns (with fixes)

**Implementation-as-criteria**
- Bad: "**Then** the system stores a bcrypt hash in the users table"
- Good: "**Then** the password is stored securely and cannot be retrieved in plaintext"

**God criterion** — too many things in one AC
- Bad: AC covers login, session creation, redirect, and audit logging
- Good: Split into AC-1 (login), AC-2 (session), AC-3 (redirect), AC-4 (audit)

**Missing the Given** — no precondition stated
- Bad: "**When** the user clicks delete **Then** the item is removed"
- Good: "**Given** a user viewing their own item **When** the user clicks delete **Then** the item is removed"

**Non-verifiable Then**
- Bad: "**Then** the system handles the error gracefully"
- Good: "**Then** the system displays 'Unable to process request' and logs the error with a correlation ID"

### Positive Patterns

**Negative Path** — explicitly spec what should *not* happen:
- "**Then** the system does not reveal whether the email exists in the system"

**State Transition** — spec before and after states:
- "**Given** an order in 'pending' status **When** payment is confirmed **Then** the order transitions to 'confirmed' status"

**Permission Matrix** — use Scenario Outline for role-based access:

```markdown
### AC-N: Role-based access control
**Given** a user with role `<role>`
**When** the user attempts to `<action>`
**Then** the system responds with `<result>`

| role | action | result |
|------|--------|--------|
| admin | delete user | success (HTTP 200) |
| member | delete user | forbidden (HTTP 403) |
| guest | delete user | unauthorized (HTTP 401) |
```

## SDLC Pipeline Integration

The acceptance criteria produced by this skill feed directly into the autonomous SDLC pipeline:

1. **Architect** — AC blocks slot into the `## Acceptance Criteria` section of the plan document. AC-N numbers provide traceability across the plan.
2. **Builder** — Each AC provides a precise TDD target. Builders write tests that verify each Given/When/Then before writing implementation code.
3. **Validator** — AC-N numbers map to PASS/FAIL rows in the validator report. Validators check each criterion independently.
4. **bdd-generate** — Structured Given/When/Then converts directly to Gherkin `.feature` files. Use `bdd-generate` to scaffold executable pytest-bdd tests from these acceptance criteria.

The handoff to `bdd-generate` is optional — acceptance criteria are valuable on their own as a specification artifact even without executable BDD tests.

## Resources

- **`references/bdd-glossary.md`** — Consult for BDD terminology definitions when the human uses unfamiliar terms or when explaining concepts. Contains one-line definitions and examples for Feature, Scenario, Given/When/Then, Background, Scenario Outline, and more.

- **`references/edge-case-checklist.md`** — Consult during Step 3 of the coaching workflow. Contains structured probing questions organized by domain (input validation, auth/authz, state integrity, concurrency, boundaries, error handling, external dependencies, UX states). Use as a prompt to surface edge cases the human hasn't considered.
