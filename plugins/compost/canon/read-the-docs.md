# Read the docs

Before writing code against something you did not write, read its current documentation. Memory of
an API is a guess with a date on it, and the date is wrong more often than it feels.

Adapted from the read-the-damn-docs skill in the retired agent-skills plugin.

## Why it matters for an agent

A model's knowledge of a library is a snapshot from training, blended across every version it saw.
It recalls option names, imports, and defaults fluently, and fluency reads as certainty. Fast-moving
APIs drift underneath that snapshot: a renamed export, a changed default, a new required scope. The
code compiles, or nearly does, and the error that follows looks like a bug in your code. Ten minutes
of reading the reference saves an hour of diagnosing a version mismatch.

The same holds for the repo itself. An ADR, a schema, an OpenAPI spec, or a package README defines a
contract. Inventing an endpoint or a prop the repo already defines elsewhere is the local version of
coding from memory.

## When to read first

- Adding, upgrading, or configuring a package, SDK, CLI, framework, model, or cloud resource.
- Anything touching auth, scopes, webhooks, billing, PII, migrations, rate limits, caching, or
  deploys, where a wrong guess is expensive or silent.
- An error that mentions deprecation, an unknown option, a missing export, or a version mismatch.
- A choice that is hard to reverse: wire formats, schemas, persistent IDs, event names.
- You notice yourself writing "usually", "probably", or "I think" about an external API.

A typo fix, a formatting change, or self-contained code with no external contract needs no
docs pass.

## What counts

Prefer the most authoritative source in reach. For this repo's behavior that is its own docs, ADRs,
schemas, generated types, and tests. For a third party it is the official reference, migration
guide, and changelog for the installed major version, found by search when the URL is not at hand,
then the package's source and types where the docs run thin. Check the installed version before
reading (`uv pip show`, `npm view <pkg> version`) so you read the right major. Blog posts and
answers on forums help debug a symptom once the contract is known; they do not define it.

## In practice

- Name the exact surface first: package, installed version, endpoint, config key.
- Read the page closest to that surface and pull out the few facts the task needs.
- When the docs and the existing code disagree, read the code path and say which one is right.
- Cite what you read when it shaped the change, in the PR or the issue ruling.
- If the docs cannot be reached, say so before relying on memory, and do not call the result
  confirmed.
