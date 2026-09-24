# Task brief for an issue worker

The brief is the only thing a worker knows about the run. It cannot see your conversation, its
siblings, or the rulings you have in your head, and a background worker cannot ask you a question
mid-task. A field you cannot fill is an issue you have not understood yet; go back to the issue.

Pass pointers for anything the worker can read itself (the issue URL, file paths, commit SHAs), and
paste only what must not drift: the acceptance criteria, the Interfaces block, and the domain terms.
Never paste the history of earlier issues; name the commits instead.

Size it to the issue. A one-file change gets the same fields collapsed into a paragraph.

## Template

```text
You are implementing issue #<n>: <title>
<issue URL>

## Where this fits
<one or two lines: the parent issue #<p>, what this issue adds, and which issues depend on it>

## Workspace
Your worktree starts from <feature branch> at <SHA>. Work only there, on branch <branch>.
<For a teammate: create it first with `git worktree add <path> -b <branch> <feature branch>`.>
Read this repo's instructions file (AGENTS.md or CLAUDE.md) before editing.

## Acceptance criteria (verbatim from the issue)
<the user story and its AC-N scenarios in Given/When/Then>

## Interfaces (verbatim from the issue)
Consumes: <what this issue relies on from earlier issues, with the commits that produced it>
Produces: <what later issues rely on; keep these names and signatures exactly>

## Domain terms
<the CONTEXT.md entries this issue uses, one line each; use these names in code>

## Rulings that bind this issue
<links to ruling comments on this issue or its neighbours, or "none">

## How to work
1. Load compost:build and follow it: fit tests into the existing suite, see each new or changed
   test fail before the code makes it pass, and replace old code rather than deprecating it.
2. Load compost:verify and run it in your worktree before you report.
3. Commit with the issue number in each message ("... (#<n>)"). Do not push, merge, or rebase.
4. Do not spawn subagents, and never a reviewer. Review runs after you report.
5. When something is ambiguous, pick the reading a careful colleague would pick, post it as a
   ruling comment on the issue (Ruling / Why / Cost if wrong), and keep going.
6. Stay inside this issue. Anything else you notice goes in your report as a follow-up.

## Report
Reply in under 15 lines:
- Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Branch and head SHA, and the commits you made (short SHA and subject)
- Each AC-N and the test that proves it
- What you ran to verify, with the result (for example "pytest: 214 passed, coverage 100%")
- Rulings you posted, as links
- Concerns and follow-ups, if any

Use DONE_WITH_CONCERNS when the work is complete but you doubt part of it. Use BLOCKED or
NEEDS_CONTEXT only when every path forward is a guess, and put the specifics in the reply.
```

## Handling the report

- **DONE:** land it (merge into the feature branch, run the suite), then review.
- **DONE_WITH_CONCERNS:** read the concerns. Correctness or scope doubts get settled before review;
  observations go to review with the diff.
- **NEEDS_CONTEXT:** give the missing context and resume the same worker.
- **BLOCKED:** change something before retrying: more context, a more capable model, a smaller issue
  (through `compost:slice`), or a ruling that settles the conflict. Never resend the same brief to the
  same model unchanged.
