# Ubiquitous language, bounded contexts, context maps

Use one vocabulary for the domain everywhere: in conversation with the user, in issues and specs,
and in the code's names. When the user says "invoice", the code has an `Invoice`, the tests talk
about invoices, and nobody calls it a "bill" or a "payment request" in one file and something else
in the next.

The idea comes from Eric Evans, *Domain-Driven Design*, along with the two that keep it honest.

- **Ubiquitous language.** The shared vocabulary of domain experts and developers, refined
  together. A term that is awkward to say in the code is a sign the model is off, and fixing the
  word often fixes the design.
- **Bounded context.** The boundary inside which one model and its language are consistent. Large
  systems do not have one model. "Account" in billing and "account" in authentication are
  different things; inside each context the word means exactly one thing.
- **Context map.** The picture of how contexts relate: which one publishes events the other
  consumes, which types are shared, where a translation layer sits.

## How the repo records it

The files follow Matt Pocock's convention. `CONTEXT.md` at the root is the glossary for a single
context: each term defined in a sentence or two, with the words to avoid listed under it. It is a
glossary and nothing else, with no implementation notes, plans, or decisions. When a repo has
several contexts, `CONTEXT-MAP.md` at the root lists them, links each context's own `CONTEXT.md`,
and states the relationships between them. Both files are created lazily, when the first term is
settled or the second context appears.

## Why it matters for an agent

An agent coins names freely, and every synonym it introduces splits one concept into two in the
reader's head. Drift in names is how two modules end up modelling the same thing differently, and
how a spec and its code quietly disagree. A glossary the agent reads before working gives it the
words to use and the words to refuse, and a context map tells it when the same word legitimately
means two things.

## In practice

- Read `CONTEXT.md` (or `CONTEXT-MAP.md`, then the relevant context's file) before naming
  anything. Use its terms in code, tests, commit messages, and issues.
- When the user uses a term that conflicts with the glossary, or a vague word that could mean two
  glossary terms, say so and settle it before building. Record the settled term right away.
- Keep general programming words out of the glossary. It holds terms specific to this domain.
- When no domain word exists for a thing you are about to name, treat that as a design question,
  not a naming chore: the concept may be missing from the model or may not belong.
