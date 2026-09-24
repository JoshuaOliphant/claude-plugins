# Boundary discipline

Validate, parse, and handle errors where data enters the system. Inside, trust the types. Keep
the logic in plain functions with no framework or vendor dependencies, and keep the shell that
talks to the outside world thin and mechanical.

Forked from the pstack principle of the same name.

## Where the boundaries are

A boundary is anywhere data crosses into or out of code you control: command-line arguments,
config files, environment variables, HTTP requests and responses, database rows, queue messages,
third-party SDK calls, files on disk, model output. At a boundary, data is untrusted and untyped.
Past it, data should already be in the domain's own types.

## Why it matters for an agent

Agents validate defensively everywhere, because every function looks like it might receive bad
input. The result is the same check repeated at five depths, each slightly different, none
authoritative, and a reader who cannot tell which one actually protects anything. Scattered
validation is noise that feels like safety.

The other half is where logic lives. Logic tangled with a web framework, an ORM, or an SDK can
only be tested by standing that dependency up. Logic in a pure function is tested by calling it.

## In practice

- Parse at the boundary: turn raw input into domain types once, reporting errors there. Config is
  validated when it is loaded, not where a value is used.
- Inside the system, do not re-check what the boundary already guaranteed. No null checks deep in
  a call chain for values that cannot be null.
- Do not let transport, storage, framework, or vendor types cross into the domain. The HTTP
  handler receives a request and passes a domain object in; the logic never sees the request.
- Put decisions in pure functions (state in, result out) and let the shell do the I/O around
  them. Two questions settle most cases: is this data crossing a boundary right now? If not,
  validating it again is redundant. Could this be a pure function the shell calls? If so,
  extract it.
- Validate at the boundary by default. Add checks at every layer only on critical paths that are
  named as such.
