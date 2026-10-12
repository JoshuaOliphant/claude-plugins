# Make mistakes impossible

When a mistake can be prevented by structure, build the structure instead of writing a rule. A
rule asks the next agent to remember; a check fails until the mistake is gone.

Adapted from pstack's `correct` skill and Matt Pocock's `retro` skill.

## Why it matters for an agent

An agent that makes a mistake twice is usually told to write it down: a line in `AGENTS.md`, a
note in the knowledge base, a sentence in a skill. Each note works only if the next agent loads it,
reads it at the right moment, and weighs it above everything else in its context. Notes pile up,
and the pile is read less carefully the longer it gets. A check costs more once and nothing after:
it runs every time, it never forgets, and it says exactly where the mistake is.

## Fix each class at the highest level that works

Fix the class of mistake, not just the instance, and go as high up this list as the mistake allows:

1. **Architecture.** Change the design so the mistake has nowhere to happen: one entry point
   instead of two, a module that owns the invariant.
2. **Types.** Make the wrong state unrepresentable, so the checker refuses it
   ([type-system discipline](type-system-discipline.md)).
3. **A lint rule whose error names the fix.** "Use `load_config()`, not `open('config.toml')`"
   gets fixed on the spot; "style violation" gets suppressed.
4. **A test.** It catches the mistake after it is written, and only where the test reaches.
5. **Docs, last.** A rule in prose is for what no check can see: judgment, taste, context.

A **mechanical** mistake (a fixed syntactic pattern, a banned API, an import shape, a file in the
wrong place) gets a deterministic check, full stop. Default to building the check over writing the
rule.

## In practice

- A class counts once it has happened twice. One slip is noise; the same slip in two sessions is
  a pattern worth a check.
- Prove each new check fails on a real past mistake. Revert the fix, or replay the commit that
  introduced it, and watch the check catch it. A check never seen failing proves nothing
  ([prove it works](prove-it-works.md)).
- Fix the instance in front of you, then build the check or file an issue for it. The instance
  is today's work; the check is what stops tomorrow's.
- Prefer a hook or CI step the repo already runs over a new tool. A check nobody runs is a rule
  with extra steps.
