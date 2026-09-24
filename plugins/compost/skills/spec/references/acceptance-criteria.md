# Acceptance criteria

Each user story carries its acceptance criteria as numbered Given/When/Then scenarios. The story
says why; the scenarios say what done means. The AC-N number follows each criterion from the spec
to the issue that implements it, the test that proves it, and verify's report.

## Format

```markdown
### 3. As a support agent, I want to cancel an order for a customer, so that I can resolve
complaints without asking them to log in

#### AC-5: Support cancels an unshipped order
**Given** an order in `pending` with no shipped lines
**When** a support agent cancels it from the admin panel
**Then** the order moves to `cancelled`
  and the customer receives the cancellation email
  and the audit log records the agent who cancelled it
```

- **Bold Given/When/Then** in markdown. Conversion to Gherkin happens only if the project wants
  feature files (see [gherkin](gherkin.md)).
- **One action per When.** If the When needs "and", it is two criteria.
- **Every Then is observable.** "Handles the error gracefully" can't be tested; "shows 'Unable to
  cancel: this order has shipped' and changes nothing" can.
- **Every criterion has its Given.** The state before the action is half the scenario.

## Order of work

1. **Happy path first.** The primary success scenario for the story. Read it back against the
   story: does it deliver the benefit?
2. **Then the edge cases.** Work through [the edge-case checklist](edge-case-checklist.md) and
   reason about how this behavior fails before you ask. The failure modes you miss here become
   the bugs that ship. Put the ones that change behavior to the user as questions in the next
   round; decide the rest as assumptions.
3. **Then merge repeats into outlines.** When three or more criteria share one shape, write one
   scenario outline with an examples table:

```markdown
#### AC-9: Cancellation is refused for orders past the window (outline)
**Given** an order in `<state>`
**When** the customer cancels it
**Then** the page shows "<message>"
  and the order stays in `<state>`

| state     | message                                        |
|-----------|------------------------------------------------|
| shipped   | This order has shipped. Start a return instead |
| delivered | This order has shipped. Start a return instead |
| cancelled | This order is already cancelled                |
```

## Patterns worth reaching for

- **Negative path:** say what must not happen. "Then the response does not reveal whether the
  email is registered."
- **State transition:** "Given an order in `pending`, When payment is confirmed, Then it moves to
  `confirmed`."
- **Permission matrix:** an outline of role by action by result for role-based access.

## Anti-patterns

| Anti-pattern | Example | Fix |
|---|---|---|
| Implementation as criterion | "Then the password is stored as a bcrypt hash" | "Then the stored password cannot be read back as plain text" |
| God criterion | One AC covering login, session, redirect, and audit | One AC each |
| Missing Given | "When the user clicks delete, Then it is removed" | "Given a user viewing their own item, When..." |
| Unobservable Then | "Then the error is handled gracefully" | "Then it shows 'Unable to process' and logs the correlation ID" |
| Compound When | "When the user edits and saves" | Two criteria, or a Given for the edit |

## Before calling them done

- Scope: is anything here that can wait? Move it to Out of scope marked `Later:`.
- Completeness: is there an actor or a state with no scenario?
- Verifiability: can a test observe every Then without reaching into internals?
