# Parent issue

The spec is posted as one issue, the parent every slice links back to. Title it with the feature
in the glossary's words ("Customers cancel unshipped orders"), not the implementation.

Write in short bullet sentences so the issue can be read at a glance. No long paragraphs, no file
paths, no code, apart from a prototype snippet that pins a decision (trimmed to the decision and
marked `From the prototype on <branch>:`).

Bounded work uses the sections marked **bounded**. Architectural work uses all of them.

## Template

```markdown
**Class:** bounded | architectural. <one line on why>

## Clarifications
<!-- bounded, architectural -->
> <the original request, word for word>
> * <one bullet per settled answer, from the refined prompt>

## Problem
<!-- architectural -->
<The problem the user faces, from their perspective. Two to four bullets.>

## Overview
<!-- bounded, architectural -->
- <the key decisions and the motivation for them; four or five bullets for bounded work>

## User stories and acceptance criteria
<!-- bounded, architectural -->

### 1. As a <actor>, I want <feature>, so that <benefit>

#### AC-1: <descriptive title>
**Given** <state before the action>
**When** <one action>
**Then** <observable outcome>
  and <further outcome>

#### AC-2: <title>
...

### 2. As a <actor>, ...

## Approaches considered
<!-- architectural -->
- **<Approach A> (chosen):** <what it is>. Wins on <...>, costs <...>.
- **<Approach B>:** <what it is>. Rejected because <...>.

## Decisions
<!-- architectural; bounded work calls this section "Changes" and keeps it to what changes
     relative to the existing system -->
- <modules built or changed, named by responsibility, not path>
- <interfaces other code depends on, and how they change>
- <data or schema changes, API contracts, interactions between parts>
- <behavior that changes because new and existing functionality now interact>

## Testing decisions
<!-- bounded, architectural -->
- Seams: <where the tests hook in; existing seams first, as high and as few as possible>
- Prior art: <the existing tests or suites these resemble>
- Test convention: <from docs/agents/testing.md>; BDD feature files: yes | no
- A good test here checks external behavior, not implementation details.

## Assumptions
<!-- bounded, architectural -->
- <each gap filled without asking, so the reader can overturn it>

## Out of scope
<!-- bounded, architectural -->
- <what this spec deliberately leaves out, and where it goes instead if anywhere>

## Evidence
<!-- only when a prototype or spike settled something -->
- `prototype/<slug>`: <the question it answered and the verdict>

## Open questions
<!-- bounded, architectural -->
- <each quoting the spec line it concerns, or "None">
```

## Notes on filling it in

- The user-story list is long for architectural work: cover every actor and every aspect of the
  feature, including the unhappy ones (the admin who revokes access, the customer whose card is
  declined). A story with no acceptance criteria is not finished.
- Number AC-N across the whole spec, not per story, so "AC-7" names one criterion everywhere:
  in slice's issues, in test names, and in verify's report.
- Deferred criteria stay in the spec marked `Later:` under Out of scope rather than disappearing,
  so nobody reopens a settled scope question.
- A local tracker writes the same content to `.scratch/<slug>/spec.md`, with the title as the
  first heading.
