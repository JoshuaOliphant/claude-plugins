# Mutation testing

Line coverage says a line ran. A mutant says whether any test would notice the line being wrong.
In compost's own `stop_guard.py`, held at 100% line coverage, cosmic-ray left 43 of 154 mutants
alive; one turned `return True` into `return False` on the branch that recognizes a typed
`/compost:implement`, and every test still passed.

Run it on the diff, not the repo. A whole-file run of that 109-line module took 94 seconds; the
same run filtered to one changed line took 11. Scoped to the branch, mutation testing costs about
what the suite costs, so it can run on every change.

## Commands by stack

Each command mutates the lines changed between the commit the branch started from and the working
tree, so uncommitted work counts. Set the base once:

```bash
base=$(git merge-base origin/main HEAD)   # the default branch, as compost:review reads it
untracked=$(git ls-files --others --exclude-standard)
[ -z "$untracked" ] || printf 'untracked, so never mutated: %s\nrun git add -N on the new sources\n' "$untracked"
```

`git diff` leaves out untracked files, so for the tools below that read it, a new module is never
mutated until `git add -N` (or a real `git add`) puts it in the index; a run with untracked sources
is not clean. `thin.py` reads untracked files itself.

### Python: thin.py survivors

compost's `thin.py` runs the mutants itself; cosmic-ray only supplies them. Each mutant is served
from memory to a child forked from a warm process, so the tree never changes and runs go side by
side. It runs a changed line's mutants against the tests that cover it, and a line no test runs,
such as a module constant or a default argument that runs only at import, against every test. It
reads git for the changed lines, untracked files included, so no `git add -N` is needed. It
refuses to start unless the covering tests pass unmutated, and it counts timeouts and crashes apart
from kills. From the directory pytest runs in:

```bash
T=${TMPDIR:-/tmp}/mutation && mkdir -p "$T"
pytest --cov=<package> --cov-context=test --cov-report= -p no:cacheprovider
coverage json --show-contexts -o "$T/contexts.json"
uv run --with cosmic-ray python ${CLAUDE_PLUGIN_ROOT}/scripts/thin.py survivors "$T/contexts.json" \
  --base "$base" --paths <source dirs> --pytest-args "-q -p no:cacheprovider --no-cov" > "$T/survivors.json"
```

It prints JSON: `survivors` (each with `module`, `line`, `operator`, and the `mutated` line) and the
counts of `changed_lines`, `mutants`, `killed`, `survived`, `timeouts` and `crashed`. It exits 0 when
every mutant is killed, 1 when any survive or time out, 2 when the baseline or git fails, and 3 when
changed lines made no mutant: comments only, or `--paths` misses the changed code. A timeout is a
mutant that made the tests hang, such as a loop that never ends; sort it like a survivor. A crash
broke the run outright, such as an annotation that no longer evaluates, and no test had to notice.
`--paths` names source, never tests. `--no-cov` keeps a coverage gate in `addopts` from failing
every run.

It runs cosmic-ray's operators only. `--operators all` adds thin's own, the breaks cosmic-ray never
makes: a deleted statement or guard, a constant return, a dropped boolean term, a changed string, a
nudged float threshold, a dropped same-type call ([kill matrix](../../thin/references/kill-matrix.md#thins-own-operators)).
A surviving string mutant is listed apart, in `survived_strings`, and doesn't fail the run, since it
is most often a message nobody reads.

### JavaScript and TypeScript: StrykerJS

Stryker has no diff mode, but `--mutate` takes line ranges (`file:start-end`, comma-separated),
so turn the diff into ranges. It needs a `stryker.config.json`, for example
`{"testRunner": "vitest", "reporters": ["clear-text", "progress"], "coverageAnalysis": "perTest"}`.

```bash
M=$(git diff -U0 "$base" -- '*.js' '*.jsx' '*.ts' '*.tsx' '*.mjs' '*.cjs' ':!*.test.*' ':!*.spec.*' ':!*.d.ts' \
  | awk '/^\+\+\+ b\//{f=substr($0,7)} /^@@/{split($3,a,/[+,]/); s=a[2]; c=(a[3]==""?1:a[3]); if(c>0) printf "%s%s:%d-%d",(n++?",":""),f,s,s+c-1}')
if [ -n "$M" ]; then npx stryker run --mutate "$M"; else echo "no JS/TS lines changed"; fi
```

Survivors print as `[Survived]` with `file:line:col`. The guard matters: an empty `--mutate`
fails with "No tests were executed". When it prints "no JS/TS lines changed", check that against
`git diff --stat "$base"` before calling the run clean.

### Rust: cargo-mutants

```bash
git diff "$base" > "${TMPDIR:-/tmp}/branch.diff"
cargo mutants --in-diff "${TMPDIR:-/tmp}/branch.diff"
```

It mutates every function the diff touches, unchanged lines in them included. Survivors print as
`MISSED src/lib.rs:10:9: ...` and land in `mutants.out/missed.txt`; add `mutants.out*` to
`.gitignore`. `--in-diff -` does not read stdin, so write the diff to a file.

### Go: gremlins

```bash
gremlins unleash --diff "$base" -S l
```

It mutates the changed lines only, uncommitted ones included. Survivors print as
`LIVED ... at x.go:12:13`. It exits 0 with survivors, even under `--threshold-efficacy`, so read
the output; its "Mutator coverage: 100.00%" means only that tests reach the code.

### Java: PIT

`mvn org.pitest:pitest-maven:scmMutationCoverage -DoriginBranch="$base"` scopes to the files the
SCM reports changed, not lines, and `destinationBranch` defaults to `master`. Not yet run by
compost; setup's proving run is the check.

## Gotchas

`thin.py` handles these for Python; the tools for the other stacks leave them to you.

- **A broken setup reports perfect tests.** Most tools count a test command that errors as a killed
  mutant: run outside `uv run`, cosmic-ray's own runner resolved `python` to an interpreter without
  pytest and reported all 154 of `stop_guard.py`'s mutants killed in 5 seconds, where the real run
  kills 111 and leaves 43. Run the suite unmutated in the same environment right before, and stop
  on a failure. A run where nothing survives on more than a few lines deserves the same suspicion.
- **A timeout counts as a kill.** cosmic-ray's runner scores a test command that outruns its
  timeout as killed, so a slow suite turns survivors into kills.
- **Read the survivors, not the score.** `cr-report`'s "surviving mutants: 18 (11.61%)" divided by
  every job, including the ones its git filter skipped; 18 of 18 run mutants had survived.
- **In-place tools leave a mutant behind when interrupted.** A timeout or Ctrl-C that stops the run
  itself can strand one. Run `git diff` afterwards and restore anything you did not write.
- **Stale bytecode.** A hand-made edit that keeps a file's size and lands in the same second as the
  last write can leave Python running the old `.pyc`. Set `PYTHONDONTWRITEBYTECODE=1`.
- **The base branch.** Diff against the commit the branch started from, the same base
  `compost:review` reads. Against a stale local `main`, every tool mutates other people's lines.

## Triage

Every surviving mutant lands in one of three places:

- **Unprotected behavior.** A test should have failed. Go back to `compost:build` and fit a case
  in, as it does for a coverage gap. Killing it with a test that asserts nothing about behavior
  (a constant, a log line's wording) is padding, the same as for coverage.
- **Equivalent.** The mutant cannot change what the program does, such as `x <= 0` against
  `x < 1` for an int. Name why in the report. It does not need a test.
- **Excluded.** It sits in a pattern `docs/agents/testing.md` already excludes, such as the
  `if __name__ == "__main__":` guard or a `sys.path.insert`. A new pattern is proposed to the user
  exactly as a coverage exclusion is.

There is no score threshold. A percentage invites killing easy mutants and leaving the one that
matters; the gate is that no survivor is left unsorted.
