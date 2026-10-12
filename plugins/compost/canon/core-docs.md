# Core docs

Keep documentation to what the code can't say, and put everything else in the code. When a doc and
the code disagree, the code is the likely truth.

## Why it works

Code is executed, so it can't be wrong about what it does. A doc is never executed, so nothing
tells anyone when it stops being true. Every doc that restates the code is a second copy of a fact,
and two copies drift. The fix is one copy: say it in the code, where the build, the type checker,
and the tests keep it honest, and delete the prose.

What the code can't say is narrow and changes slowly: why the system is shaped this way, which
alternatives were rejected, what the domain's words mean, how to install and run it, how to work in
the repo. Those few files are the core docs. Because they change slowly and say little, they can be
kept true.

## Why it matters for an agent

An agent treats every doc it reads as instructions. A stale architecture page or a finished plan
looks exactly as authoritative as the code, so the agent builds on the stale version, or spends
its context reconciling the two. A human learns which pages to ignore; an agent starts fresh every
session and never does. Fewer docs means less wrong context, and the core docs it does read are
ones that stay true.

## In practice

- Prefer, in order: a name that says it, a type or check that enforces it, a test that shows it, a
  comment beside the code that explains why, and only then a core doc.
- The core docs: `README.md`, `AGENTS.md`, `CONTEXT.md` (or `CONTEXT-MAP.md`), `docs/adr/`, and
  whatever a repo adds to the list in `docs/agents/docs.md`.
- ADRs are records of a decision at a point in time. When the code contradicts one, supersede it
  with a new ADR or fix the code; never edit the record to match.
- Plans and specs belong in the issue tracker, where they close when the work is done. A plan file
  in the repo outlives its work and reads as current.
- Code is the likely truth, not the certain one. A doc requirement backed by a test, an issue, or
  an ADR points at a bug, not drift.
- `compost:prune` checks the docs against the code and moves what is worth keeping into it.
