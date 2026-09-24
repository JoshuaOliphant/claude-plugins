# Tracing a failure to its origin

The line that throws is where the bug became visible, not where it started. Fixing it there leaves
the bad value in flight for the next caller to trip over.

## Trace backward through the call chain

1. Write down the symptom exactly: `git init failed in ~/project/packages/core`.
2. Find the code that directly produced it: `execFile('git', ['init'], { cwd: projectDir })`.
3. Ask what called it, and with what value. Walk up one caller at a time:
   `createSessionWorktree(projectDir)` ← `Session.initializeWorkspace()` ← `Session.create()` ← a test.
4. At each level, check the value you care about. Here `projectDir` was `''`, and an empty `cwd`
   resolves to the process's working directory: the source tree.
5. Keep going until you reach the code that first produced the bad value. Here a test read
   `context.tempDir` at module load, before the setup hook had filled it in.
6. Fix it there. In the example, `tempDir` became a getter that throws when read before setup. The
   `git init` call site needed no change.

## When you can't follow it by reading

Capture the stack at the moment of the dangerous operation, before it runs rather than after it
fails, along with the context that matters:

```typescript
const stack = new Error().stack;
console.error('[DEBUG-7c1e] git init', { directory, cwd: process.cwd(), stack });
```

In tests, write to stderr directly; the project's logger may be silenced under test. Run the suite,
filter on the tag, and look at which test files and line numbers appear, and whether it is always the
same test or the same argument.

## Which test pollutes shared state

When something appears during a test run (a stray file, a leftover row, a changed global) and you
don't know which test causes it, run the test files one at a time and check for the pollution after
each. [`../scripts/find-polluter.sh`](../scripts/find-polluter.sh) does this for any test runner:

```bash
scripts/find-polluter.sh .git 'uv run pytest' tests/test_*.py
scripts/find-polluter.sh .git 'npx vitest run' src/**/*.test.ts
```

It stops at the first file that creates the path and prints it.

## Several components in one path

When a request crosses CI, a build script, a signing step, a service, and a database, don't read them
all. Add one line of logging at each component's entry and exit (what arrived, what left, which
config and environment it saw), run once, and see where good input turns into bad output. Then study
only that component.

## Restart-only failures

When something works until a restart, suspect persistent state before code: config files, caches,
lock files, serialized sessions, migrations half applied. Clear one piece of state at a time and
re-run the loop. If clearing a file restores the behaviour, the root cause is that the file can be
written in a shape the loader doesn't accept; validate it where it is loaded and fix whatever wrote
it.

## Working versus broken

When similar code works (another endpoint, the previous release, the same function with other input),
list every difference between the two paths, however small, before deciding any of them can't matter.
The difference that "can't matter" is often the one that does.
