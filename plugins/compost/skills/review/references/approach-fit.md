# Approach fit

A line-by-line review asks whether the code is right. This asks whether it is the right code: would
someone who knew the codebase well, and had never seen this branch, have solved the problem this
way? The judge can only answer honestly if it designs before it reads, so it gets the problem and
not the solution.

Before spawning the judge:

- Resolve the base and tip to commit hashes, so it reads exactly the code you mean.
- Check that `git diff <base>...<tip>` contains only this branch's work. A stale base or a merged-in
  branch has the judge assessing code nobody on this issue wrote; if no clean base exists, list the
  paths to ignore.
- Write the problem as the user would describe it: what should behave differently, and for whom.
  Leave out any mechanism, library, or data structure; naming one hands the judge the answer.

Spawn one subagent with this prompt, placeholders filled in:

---

Decide whether a branch solves its problem in the way this codebase should solve it.

The problem: <problem, in behavior terms only>
Before the change: commit <base>. After: commit <tip>.

Work in this order, and do not open the diff until step 3.

1. **Learn the codebase as it stood.** Use `git show <base>:<path>` to read the project's
   instruction files, `CONTEXT.md`, the ADRs in `docs/adr/`, and the modules this problem would
   naturally touch. Note the conventions a newcomer would be expected to follow.
2. **Design it yourself, three ways.** Sketch three genuinely different solutions: the smallest
   change that works, the one that generalizes, and the one that best fits existing patterns. For
   each, one paragraph: what it changes, what it reuses, what it costs later.
3. **Read what was built.** Read the diff and the changed files whole.
4. **Compare.** Which of your designs is it closest to, and where does it diverge? For each
   divergence, say whether it is better, worse, or just different, and why. Call out:
   - existing code it duplicates instead of reusing or extending;
   - conventions of this codebase it breaks, even for a good reason;
   - inputs it reads that are not passed in (environment, filesystem, clocks, globals, process
     state), since those are where hidden coupling lives;
   - whether it removes the cause of the problem or routes around it, and whether it covers the
     whole problem.
5. **Verdict.** One of: fits; fits with named changes; a better approach exists. For the last,
   describe that approach concretely enough that someone could build it.

Cite file:line for every claim. Report the verdict first, then the divergences, then your three
designs in brief.
