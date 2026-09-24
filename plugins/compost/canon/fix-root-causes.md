# Fix root causes

When something breaks, trace the symptom back to the cause and fix it there. A change that makes
the symptom disappear while the cause remains is not a fix.

Forked from the pstack principle of the same name.

## Why it matters for an agent

Symptom fixes are the path of least resistance: wrap it in a try, add a null check, retry on
failure, special-case the input that crashed. Each one makes the immediate error go away, so the
agent's check passes and it moves on. The real defect is still there, now harder to find because
its signal is suppressed, and the next agent has one more guard to reason around. Workarounds
accumulate; root-cause fixes are slower once and cheaper every time after.

A workaround also usually arrives with a comment explaining why it is needed. If the code needs a
paragraph to justify itself, the code is what is wrong.

## How to get to the cause

- **Reproduce first.** A bug you cannot trigger on demand is a bug you cannot confirm fixed. Get a
  failing test or a scripted reproduction before changing anything.
- **Ask why until the answer is in the design, not the data.** "It crashed on a null" is the
  symptom. Why was it null? Why did nothing upstream reject it? The fix belongs at the first place
  the system should have known better, often a boundary that failed to parse its input.
- **Instrument instead of guessing.** Read the actual error, the full log, the real value. Add
  logging or a breakpoint to see what happened. Three guesses in a row is a sign to stop guessing.
- **Suspect state when behavior changes across a restart.** Config files, caches, lock files, and
  serialized state outlive the code that wrote them. If clearing one restores behavior, the fix is
  validating that state, not clearing it.

## In practice

- Do not add a guard to silence a failure you do not understand. Understand it, then decide.
- After fixing one instance, search for the same pattern elsewhere and fix those too, or file an
  issue listing them.
- Never read past a failing log line or a warning. It carries the information you need.
- Keep the reproduction as a regression test, seen failing before the fix and passing after.
