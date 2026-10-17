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
```

### Python: cosmic-ray

mutmut 3 refuses flat modules that tests import through `sys.path` (a `scripts/` directory, a
conftest that inserts a path): it stops with "none match any mutant key". cosmic-ray mutates the
file in place and runs any test command, so it works with every layout. When the repo already runs
mutmut, keep it, but it has no line filter: narrow `source_paths` to the files the diff touches.

Add `cosmic-ray` as a dev dependency (`uv add --dev cosmic-ray`) and commit a config, for example
`cosmic-ray.toml`:

```toml
[cosmic-ray]
module-path = "src/pkg"            # a file or a directory; it must hold every file the diff changes
timeout = 30.0
excluded-modules = []
test-command = "python -m pytest -x -q -p no:cacheprovider --no-cov"

[cosmic-ray.distributor]
name = "local"
```

Then, as one command so a failed baseline stops it:

```bash
filter=$(mktemp) && printf '[cosmic-ray.filters.git-filter]\nbranch = "%s"\n' "$base" > "$filter" \
  && uv run cosmic-ray baseline cosmic-ray.toml \
  && rm -f .cosmic-ray.sqlite \
  && uv run cosmic-ray init cosmic-ray.toml .cosmic-ray.sqlite \
  && uv run cr-filter-git --config "$filter" .cosmic-ray.sqlite \
  && PYTHONDONTWRITEBYTECODE=1 uv run cosmic-ray exec cosmic-ray.toml .cosmic-ray.sqlite \
  && uv run cr-report .cosmic-ray.sqlite --surviving-only --show-diff
```

The filter only removes mutants, so a changed file outside `module-path` gets none and reads as
clean: compare `git diff --stat "$base"` with what the report mutated.

`cr-filter-git` reads its base only from a config file and defaults to `master`, so the base goes
in a throwaway one rather than the committed config.

Add `.cosmic-ray.sqlite` to `.gitignore`. `--no-cov` keeps a coverage gate in `addopts` from
failing every mutant run; drop it when the project has no pytest-cov.

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

- **Read the survivors, not the score.** `cr-report`'s "surviving mutants: 18 (11.61%)" divides
  by every job, including the ones the git filter skipped; on that run 18 of 18 run mutants
  survived. Count the mutants that ran and the ones that survived yourself.
- **Stale bytecode.** A mutant that keeps a file's size and lands in the same second as the last
  write can leave Python running the old `.pyc`. Set `PYTHONDONTWRITEBYTECODE=1`.
- **In-place tools leave a mutant behind when interrupted.** cosmic-ray restores each file after
  its mutant, but a timeout or Ctrl-C that stops the run itself can strand one. Run `git diff` afterwards and restore
  anything you did not write.
- **A broken setup reports perfect tests.** cosmic-ray counts a test command that errors as
  a killed mutant. Run outside `uv run`, cosmic-ray's `python` resolved to an interpreter without
  pytest and reported all 154 of `stop_guard.py`'s mutants killed in 5 seconds, where the real
  run kills 111 and leaves 43. Run the baseline (`cosmic-ray baseline`, or the stack's suite on the
  unmutated tree) in the same environment right before the run, and stop on a non-zero exit. A
  run where nothing survives on more than a few lines deserves the same suspicion.
- **The base branch.** Diff against the commit the branch started from, the same base
  `compost:review` reads. Against a stale local `main`, the filter mutates other people's lines.

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
