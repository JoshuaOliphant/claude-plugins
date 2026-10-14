# Domain languages

Program close to the problem domain. When the domain's rules keep arriving in the same shape and
change more often than the code that runs them, let them be written in the domain's own terms,
as data or a small language, and keep one engine that reads them.

The idea comes from Andy Hunt and Dave Thomas, *The Pragmatic Programmer* ("Domain Languages"). It
is the step past [ubiquitous language](ubiquitous-language.md) and [model the
domain](model-the-domain.md): the glossary names the concepts, the model gives each one a home,
and a domain language lets the rules themselves be stated in those words, readable by the people
who own them.

## The kinds, cheapest first

- **A data language.** A table of rules in TOML, YAML, or JSON, parsed into typed models when it
  is loaded ([boundary discipline](boundary-discipline.md)). No grammar to write; the format's
  parser and the type check do the work. This is the default.
- **An internal language.** A plain API in the host language that reads like the domain: builder
  calls, a registry of decorated functions, a fluent chain. It gets the host's tooling, tests,
  and error messages for free, and can express logic a data file cannot.
- **An external language.** Its own syntax and parser. It costs a grammar, error messages people
  can act on, and editor support, all of which someone maintains forever. Almost never justified
  inside one project; reach for it only when non-programmers must write rules a data file cannot
  hold.

## The signs it would pay

- A dict of rules or an if/elif chain that grows by one entry per feature, in the same shape.
- The same rule restated in several files, each copy drifting.
- The person who decides the rules (pricing, routing, permissions, schedules) is not the one who
  edits the code, and every change goes through a developer as translation.
- Specs that are mostly tables: input combinations and the outcome each one gets.

## Why it matters for an agent

An agent extends whatever shape it finds, and an if/else chain invites one more branch with one
more special case. A rule in a narrow data language, validated at load, has nowhere to put that
branch: the type rejects it, or it has to be a new kind of rule, which is a design question the
agent must raise instead of quietly answering. The language limits what can go wrong.

The opposite risk is just as real. Agents enjoy inventing languages, and a grammar written in an
afternoon becomes a parser nobody wants to own. The cost rule below is what keeps that in check.

## In practice

- Do not spend more effort on the language than it will save. Count the rules that exist and the
  changes they get, not the ones you imagine.
- Start with data. Move to an internal language only when the rules need logic a table cannot
  hold, and to an external one only after both have failed for a reason you can name.
- Name the language's keys and keywords from `CONTEXT.md`. A rule file that uses different words
  from the glossary is a second vocabulary, not a domain language.
- Parse the rules into domain types at the edge and fail loudly on an unknown key or value; the
  engine trusts what it is handed.
- Test the engine through a few real rule files, and treat each rule file change as a change to
  behavior: it gets a test when it carries a decision.
