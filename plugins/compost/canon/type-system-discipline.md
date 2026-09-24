# Type-system discipline

Treat the type checker as a proof assistant. Shape the types so impossible states cannot be
built, mismatched values cannot be passed, and an unhandled case fails the check instead of
failing in production. This holds in any language with a static checker, including Python under
a type checker such as ty or mypy.

Forked from the pstack principle of the same name.

## Why it matters for an agent

Every case the types let a caller ignore is a runtime failure the checker could have stopped. For
an agent, the checker is also the cheapest reviewer available: it runs in seconds, it is never
tired, and it tells the next agent exactly where to add a case when a variant is added. Loose types
push that knowledge into comments and memory, where agents lose it.

## The patterns

- **Make illegal states unrepresentable.** Model alternatives as a union of distinct shapes, not
  one record with optional fields whose valid combinations live in someone's head. A task with
  `completed: bool` and `completed_at: datetime | None` admits a completed task with no
  completion time. Model it as open or done-at-a-time instead.
- **Brand semantic primitives.** A user id and an order id are both strings, and should not be
  interchangeable. Give them distinct types (`NewType` in Python, branded types in TypeScript,
  newtypes in Rust) and validate once at creation.
- **External data is untyped until parsed.** JSON, rows, environment variables, and arguments get
  parsed into typed models at the boundary; see [boundary discipline](boundary-discipline.md).
- **Do not lie to the checker.** Casts, `Any`, and ignore comments are latent crashes. Prove the
  fact (validate, narrow, fix the model) or treat the cast as a known hazard.
- **Let the checker enforce exhaustiveness.** Matches over a union end in the language's
  exhaustiveness idiom (`assert_never` in Python, a `never` binding in TypeScript) so a new
  variant breaks the build at every place that must handle it.
- **Derive from the authoritative schema.** When an OpenAPI spec, protobuf, migration, or pydantic
  model defines a shape, generate or import the type from it rather than writing a parallel one.

## In practice

- If you can write a comment explaining which combinations of fields are valid, split the type.
- If two parameters share a primitive type but mean different things, brand them.
- Trace every cast and `Any` to where the value entered the system, and parse there instead.
- Strengthen a type only where a runtime check or "should never happen" branch shows it is too
  weak, then stop. The goal is making operations total, not describing data as precisely as
  possible.
