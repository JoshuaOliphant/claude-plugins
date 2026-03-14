# Autoloop Troubleshooting

Common issues and diagnostics when an autoloop run doesn't behave as expected.

## "The agent stopped after a few iterations"

The NEVER STOP directive may not be strong enough for the model being used. Options:
- Add more emphatic language to program.md
- Check if the agent hit a context limit (very long output flooding context)
- Ensure output is redirected to run.log, not printed to stdout

## "Every experiment crashes"

The mutable artifact scope may be too broad. Narrow what the agent is allowed to change, or check that the execution environment is stable (dependencies installed, paths correct). Also check that quality gate thresholds in `auto/run.sh` aren't too strict — a threshold of 0 lint issues when the baseline has 3 will fail every time.

## "The agent modified auto/run.sh"

The program.md explicitly forbids this, but if it happened, restore from git: `git checkout main -- auto/run.sh`. Consider adding stronger language to program.md or making the file read-only: `chmod 444 auto/run.sh`.

## "Metric isn't improving"

The metric may not be responsive to the kinds of changes being made. Check:
- Is the metric actually affected by the mutable file?
- Is the change space too narrow? (e.g., tuning one hyperparameter that's already optimal)
- Is the metric noisy? (random seed variation exceeding improvement signal)

## "Agent makes the same change repeatedly"

The agent isn't learning from results.tsv. Check:
- Is results.tsv being read between iterations?
- Are descriptions specific enough to distinguish experiments?
- Try adding: "Before each experiment, read results.tsv and explicitly state what you learned from past attempts."

## "Git state got messy"

If the branch is in a bad state:
```bash
git stash                    # Save any uncommitted work
git log --oneline -20        # See recent history
git reset --hard {good_commit}  # Reset to last known good state
```
