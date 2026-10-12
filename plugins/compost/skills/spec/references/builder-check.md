# Builder check

The author of a spec can't see its gaps: their own context fills every hole as they read. The
builder check hands the spec to a reader with none of that context, someone who has to plan the
build from the page alone, and asks what they would still need to know.

## Send it

Once the draft spec is written down (a file, or the issue body you are about to post), dispatch a
fresh general-purpose subagent. Fresh means it has not seen this conversation; pass it only the
spec. Fill in the role and the path:

```
You are an experienced [ROLE, e.g. "backend engineer on this codebase"]. A spec has landed on
your desk and your job is to plan how to build it. Its author is unreachable: whatever the page
does not say, you would have to guess.

Read [SPEC_PATH]. You may read the code it touches to check your guesses.

List only the questions you would need answered before you could plan the build with confidence:
the places where you would be guessing and a wrong guess would change what gets built. For each,
give the question, the spec line it concerns, and what changes in the plan depending on the
answer. Most important first.

Leave out anything the spec deliberately leaves to the builder, anything you could settle
yourself without regret, and comments on wording or format.

If nothing that matters is left, reply "nothing important left".
```

## Sort what comes back

Each question lands in one of three piles:

- **Already answered.** The spec or the interview settled it, but the builder couldn't find it.
  The answer is in your head or the conversation, not on the page: fold it into the spec where the
  builder looked for it.
- **Minor.** A wrong guess would cost little, or there is an obvious conservative reading. Settle
  it, put the decision in the spec, and add it to the refined prompt as an `(assumed)` bullet
  ([refine-prompt](refine-prompt.md)) so the user can overturn it.
- **Theirs.** A decision that changes what gets built and that only the user can make. Add it to
  the open questions, quoting the spec line, in the format in [questions](questions.md).

Re-run the check after a pile of fixes only if they changed the spec's shape; a few folded-in
sentences don't need a second reader. "Nothing important left" is a fine result; say so.

## No subagent tool

Do the check yourself. Read the spec top to bottom as that builder would, pretending the
interview never happened, and write down every place you would have to guess. Then sort them the
same way.
