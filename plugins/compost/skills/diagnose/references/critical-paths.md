# Layered validation on named critical paths

The default is [boundary discipline](../../../canon/boundary-discipline.md): validate where data enters
the system, parse it into types that can only hold valid values, and trust those types inside. Checks
repeated at every hop are noise, they drift out of step with each other, and they hide where a value
is actually guaranteed.

The exception is a path whose failure is expensive or irreversible and that the user or the project's
docs have named as critical: moving money, deleting data, granting access, running shell commands in
the wrong directory. There, after fixing the root cause, make the bug structurally impossible by
adding a check at each layer the value passes through. Don't extend this to a path because it feels
important; it needs to be named.

## The layers

1. **Entry**: reject invalid input where it crosses into the system (empty, missing, wrong kind).
2. **Operation**: the function that does the dangerous thing refuses a value that makes no sense for
   it, even if the entry check should have caught it; another caller may not go through that entry.
3. **Environment guard**: refuse the operation in a context where it is never right, such as running
   `git init` outside a temp directory during tests, or a destructive migration against production
   without an explicit flag.
4. **Forensics**: log the context (inputs, working directory, caller stack) just before the
   operation, so the next failure explains itself.

## Applying it

1. Trace the data flow from where the value is born to where it does damage.
2. List every point it passes through.
3. Add the check that belongs at each layer, no more.
4. Test each layer on its own: bypass the entry check and confirm the operation check catches it.

## Example

An empty `projectDir` made `git init` run in the source tree. The root fix made the test fixture throw
when read too early. Because running git in the wrong directory corrupts a checkout, the path was
named critical, and it also gained: `Project.create()` rejects an empty or missing directory, the
workspace manager rejects an empty path, `git init` refuses to run outside the temp directory under
test, and a stack is logged before each `git init`.
