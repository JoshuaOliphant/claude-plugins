# Mutation testing

Line coverage says a line ran. A mutant says whether any test would notice the line being wrong.
In compost's own `stop_guard.py`, held at 100% line coverage, cosmic-ray left 43 of 154 mutants
alive; one turned `return True` into `return False` on the branch that recognizes a typed
`/compost:implement`, and every test still passed.

Run it on the diff, not the repo. A whole-file run of that 109-line module took 94 seconds; the
same run filtered to one changed line took 11. Scoped to the branch, mutation testing costs about
what the suite costs, so it can run on every change.

## Commands by stack

Each command mutates only the lines changed since `<base>`, the commit the branch started from.

### Python: cosmic-ray

mutmut 3 refuses flat modules that tests import through `sys.path` (a `scripts/` directory, a
conftest that inserts a path): it stops with "none match any mutant key". cosmic-ray mutates the
file in place and runs any test command, so it works with every layout. When the repo already runs
mutmut, keep it, but it has no line filter: narrow `source_paths` to the files the diff touches.

Add `cosmic-ray` as a dev dependency (`uv add --dev cosmic-ray`) and commit a config, for example
`cosmic-ray.toml`:

```toml
[cosmic-ray]
module-path = "src/pkg"            # a file or a directory
timeout = 30.0
excluded-modules = []
test-command = "python -m pytest -x -q -p no:cacheprovider --no-cov"

[cosmic-ray.distributor]
name = "local"
```

Then, with `<base>` as a branch name or SHA:

```bash
filter=$(mktemp) && printf '[cosmic-ray.filters.git-filter]\nbranch = "%s"\n' "<base>" > "$filter"
rm -f .cosmic-ray.sqlite
uv run cosmic-ray init cosmic-ray.toml .cosmic-ray.sqlite
uv run cr-filter-git --config "$filter" .cosmic-ray.sqlite
PYTHONDONTWRITEBYTECODE=1 uv run cosmic-ray exec cosmic-ray.toml .cosmic-ray.sqlite
uv run cr-report .cosmic-ray.sqlite --surviving-only --show-diff
```

`cr-filter-git` reads its base only from a config file and defaults to `master`, so the base goes
in a throwaway one rather than the committed config.

Add `.cosmic-ray.sqlite` to `.gitignore`. `--no-cov` keeps a coverage gate in `addopts` from
failing every mutant run; drop it when the project has no pytest-cov.

## Gotchas

- **Read the survivors, not the score.** `cr-report`'s "surviving mutants: 18 (11.61%)" divides
  by every job, including the ones the git filter skipped; on that run 18 of 18 run mutants
  survived. Count the mutants that ran and the ones that survived yourself.
- **Stale bytecode.** A mutant that keeps a file's size and lands in the same second as the last
  write can leave Python running the old `.pyc`. Set `PYTHONDONTWRITEBYTECODE=1`.
- **In-place tools leave mutants behind when killed.** cosmic-ray restores each file after its
  mutant, but a timeout or Ctrl-C mid-run can strand one. Run `git diff` afterwards and restore
  anything you did not write.
- **Baseline first.** The suite must be green before the run, or every mutant counts as killed.
  `compost:verify` runs this after its gates, so that holds there; run `cosmic-ray baseline` when
  using it on its own.
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
