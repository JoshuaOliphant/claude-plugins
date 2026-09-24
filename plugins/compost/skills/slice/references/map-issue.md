# Map issue

Some work is too big and too foggy to slice: the way from here to the destination isn't visible
yet, and guessing at slices would produce issues that get rewritten. A map charts the way instead.
It is one issue on the tracker, labelled `map`, whose sub-issues are decisions rather than slices
of a build. The map is done when nothing is left to decide; then the work gets sliced.

Refer to maps and decisions by title in everything the user reads, with the number inside the
link. A wall of bare numbers is illegible.

## The map body

The map is an index, not a store. Each decision lives in exactly one place, its sub-issue; the map
gives a one-line gist and a link.

```markdown
## Destination

<What reaching the end looks like: a spec to slice, a decision locked, a migration done. One or
two lines. Every session reads this before choosing a decision.>

## Notes

<The domain, the skills every session should use, standing preferences for this effort.>

## Decisions so far

- <closed decision title> (#<n>): <one-line gist of the answer>

## Not yet specified

<Questions you can see coming but can't yet phrase sharply, because they hang on open decisions.
Write as loosely as the view allows.>

## Out of scope

- <closed decision title> (#<n>): <why it sits past the destination>
```

## Decision sub-issues

Each decision is a sub-issue of the map, labelled `decision`, with the question as its body:

```markdown
**Kind:** research | prototype | interview | task

## Question

<The decision or investigation this sub-issue resolves.>
```

- **Research:** a fact a decision waits on, from docs, APIs, or knowledge outside the repo. A
  subagent can resolve it alone.
- **Prototype:** a question about how something should look or behave, settled by building
  something cheap to react to (see `compost:spec`'s prototype reference).
- **Interview:** a decision only the user can make, settled in `compost:spec`-style rounds. Never
  answer the user's side yourself while they are there to answer. In an unattended run, take your
  recommendation, mark it (assumed) in the resolution comment, and keep going; the user can
  overturn it later.
- **Task:** manual work that must happen before a decision can be made (provisioning access,
  signing up for a service to judge its API). Done alone where possible, otherwise handed to the
  user as a precise checklist.

Wire blocking edges in a second pass, once every sub-issue has a number. The frontier is the open,
unblocked, unassigned decisions.

## Fog or decision?

The test is whether you can state the question precisely now, not whether you can answer it now.

- **Decision sub-issue** when the question is sharp, even if it is blocked.
- **Not yet specified** when you can't phrase it that sharply yet. Don't pre-slice fog into
  pieces; one patch may become several decisions, or none, once the frontier reaches it.

Work past the destination is out of scope, not fog. Close any sub-issue that turns out to sit
there and give it a line under Out of scope.

## Charting the map

1. Settle the destination with the user first, in an interview round; it fixes the scope.
2. Survey the whole space breadth-first for open decisions and the first steps takeable now. If
   this turns up no fog, you don't need a map: slice the work directly.
3. Create the map with Destination, Notes, and Not yet specified filled in.
4. Create the decision sub-issues you can state sharply, then wire their blocking edges.
5. Send a subagent after each research decision in parallel; each posts its finding as the
   resolution comment.

## Working the map

1. Read the map body, not every sub-issue.
2. Take the decision the user names, or the first one on the frontier. Assign it to yourself before
   any work, so a parallel session skips it.
3. Resolve it, reading related decisions in full as needed.
4. Post the answer as a resolution comment, close the sub-issue, and add its gist to Decisions so
   far.
5. Add sub-issues for questions the answer made sharp, removing them from Not yet specified. Update
   or close decisions the answer made moot.

Research decisions can run in parallel through subagents. Other sessions may be editing the map at
the same time, so re-read it before writing.

The tracker commands for sub-issues, dependencies, claiming, and the frontier query are in
`docs/agents/issue-tracker.md` under "Map operations".
