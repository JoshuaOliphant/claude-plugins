# Deeper ask

Run this after classifying, for Bounded and Architectural requests. A Spike skips it: a feasibility
question would turn into a research project. It makes the request deeper, never bigger: the same
goal, reached with what a field-leading practitioner would use. Source: Felix Rieseberg, "How to be
more ambitious" (felixrieseberg.com, 13 October 2026), the Depth technique.

## The prompt

> I want a deeper version of this task, not a bigger one. Before rewriting it: (1) say what a top professional in this field would do here that I'm not asking for; (2) name the rawest material they would start from instead of what has already been digested for me; (3) name the specific methods and tools they would use; (4) say what, other than you or me, would show the result is right. Then rewrite my prompt to ask for exactly that.

## Answer it yourself

The four answers are facts, so find them rather than asking: the code, the logs, the running
system, upstream docs ([read the running system](../../../canon/read-the-running-system.md)). One or
two lines each, shown to the user.

1. **What a professional would do that the request omits.** A method or practice, never a persona:
   "check how the existing limiter counts per key", not "think like a security engineer".
2. **The rawest material.** Primary sources over summaries: the real data, the production sample,
   the upstream spec, the existing code path. Say where it lives, and read it before the interview
   when it is within reach. Check what the request takes for true against it.
3. **The methods and tools.** What the practitioners use (a database and a statistical test over a
   markdown table; the project's own test runner over a hand-run check). Name the real tool, and
   the one already in this repo when there is one.
4. **The independent check.** Something that is neither the author nor the agent: an existing test
   suite, a reference implementation, a published standard, a real sample, a tool the agent can run
   for immediate feedback. "Do not ask the model to judge itself." Where nothing independent
   exists, say so; do not invent one.

## Use the answers

- Ask once whether to adopt the deeper version, as one lettered question in the first interview
  round with your recommendation ([questions](questions.md)). Unattended, take the recommendation
  and mark it `(assumed)`. So does a request that already lives in a settled issue or doc, where
  there is no interview: take the recommendation as `(assumed)` and carry on.
- Record the outcome as bullets in the refined prompt ([refine prompt](refine-prompt.md)). The
  original request stays word for word; the deeper rewrite is bullets under it, not a replacement.
- Answers 1 to 3 become constraints and edge cases in the spec. Answer 4 becomes at least one AC-N
  that names the independent check, in terms `compost:verify` can map to something runnable. If
  none exists, list that under open questions.
- Cut anything that makes the work bigger rather than deeper ([subtract before you add](../../../canon/subtract-before-you-add.md)),
  unless the user accepts it in the adoption question.
