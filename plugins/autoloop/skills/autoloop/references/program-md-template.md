# {PROJECT_NAME}

This is an experiment to have an LLM autonomously optimize {WHAT_IS_BEING_OPTIMIZED}.

## Objective

{OBJECTIVE_DESCRIPTION}

The optimization target is {METRIC_NAME} ({METRIC_DIRECTION} is better).
{ADDITIONAL_GOAL_CONTEXT}

## Metrics

- **Primary (optimization target)**: `{METRIC_NAME}` ({METRIC_UNITS}, {METRIC_DIRECTION} is better)
{SECONDARY_METRICS_LIST}

## How to Run

Run `./auto/run.sh` — it runs quality gates in sequence (fast tests first, then conformance/lint, then the benchmark), outputting `METRIC key=value` lines on success. If any gate fails, the script exits non-zero and the agent should revert.

**Do NOT modify `auto/run.sh`.** It is the immutable measurement pipeline.

## Files in Scope

These are the files the agent reads for context and strategy:
{IN_SCOPE_FILES_LIST}

## Off Limits

Do NOT modify these files. They are read-only context:
{OFF_LIMITS_FILES_LIST}
- `auto/run.sh` — the runner script. Measurement pipeline is immutable.
- `results.tsv` — log file, append-only (never committed to git).

## Setup

To set up a new experiment run, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar11`). The branch `autoloop/{tag}` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b autoloop/{tag}` from current main.
3. **Read the in-scope files**: Read all files listed in "Files in Scope" above for full context.
4. **Verify preconditions**: {PRECONDITIONS_CHECK}
5. **Initialize results.tsv**: Create `results.tsv` with just the header row. The baseline will be recorded after the first run.
6. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off the experimentation.

## Experimentation

{EXECUTION_CONTEXT}

**What you CAN do:**
- Modify `{MUTABLE_FILE}` — this is the only file you edit. {WHAT_IS_FAIR_GAME}.

**What you CANNOT do:**
- Modify any other source files. They are read-only.
- Modify `auto/run.sh` or anything in `auto/`. The measurement pipeline is sacred.
- Install new packages or add dependencies.

**The goal is simple: get the {METRIC_DIRECTION} {METRIC_NAME}.** {ADDITIONAL_GOAL_CONTEXT}

**Resource constraints**: {RESOURCE_CONSTRAINTS}

**Simplicity criterion**: All else being equal, simpler is better. A small improvement that adds ugly complexity is not worth it. Conversely, removing something and getting equal or better results is a great outcome — that's a simplification win. When evaluating whether to keep a change, weigh the complexity cost against the improvement magnitude.

**The first run**: Your very first run should always be to establish the baseline, so run the command as-is without modifications.

## Output format

Run the experiment via the runner script:

```bash
./auto/run.sh > run.log 2>&1
```

The script runs tiered quality gates (fast tests → conformance/lint → benchmark). If any gate fails, the script exits non-zero — treat this as a crash.

On success, the last lines of output contain structured metrics:

```bash
grep '^METRIC ' run.log
```

Expected output format:
```
{METRIC_OUTPUT_EXAMPLE}
```

Parse the primary metric ({METRIC_NAME}) from the `METRIC {METRIC_KEY}=` line.
{SECONDARY_METRICS_PARSE_GUIDANCE}

## Logging results

When an experiment is done, log it to `results.tsv` (tab-separated, NOT comma-separated).

The TSV has a header row and {RESULTS_COLUMN_COUNT} columns:

```
{RESULTS_HEADER}
```

1. git commit hash (short, 7 chars)
2. {METRIC_NAME} achieved — use 0 for crashes
{SECONDARY_METRIC_COLUMNS}
3. status: `keep`, `discard`, or `crash`
4. short text description of what this experiment tried

Example:

```
{RESULTS_HEADER}
{RESULTS_EXAMPLE_ROWS}
```

## The experiment loop

The experiment runs on a dedicated branch (e.g. `autoloop/mar11`).

LOOP FOREVER:

1. Look at the git state: the current branch/commit we're on.
2. Read `results.tsv` and the Progress Log below. Explicitly state what you learned from past attempts before proposing a new change.
3. Propose a change to `{MUTABLE_FILE}` based on your understanding of the domain, previous results, and ideas from the context files.
4. git commit the change.
5. Run the experiment: `./auto/run.sh > run.log 2>&1`
6. Extract the results: `grep '^METRIC ' run.log`
7. If the grep is empty or the command failed (non-zero exit), the run crashed. Run `tail -n 50 run.log` to read the error and attempt a fix. If you can't fix it after a few attempts, give up on this idea.
8. Record the results in results.tsv (do NOT commit results.tsv — leave it untracked by git).
9. If {METRIC_NAME} improved ({METRIC_DIRECTION}), you "advance" the branch, keeping the git commit. Also update the Progress Log section below with a one-line entry.
10. If {METRIC_NAME} is equal or worse, git reset back to where you started.

**Timeout**: Each experiment should take approximately {TIME_BUDGET}. If a run exceeds {TIMEOUT_LIMIT}, kill it and treat it as a failure (discard and revert).

**Crashes**: If a run crashes, use your judgment: If it's something simple to fix (typo, missing import), fix and re-run. If the idea is fundamentally broken, log "crash" and move on.

## Strategy guidance

{STRATEGY_GUIDANCE}

## Baseline

- **Commit**: {BASELINE_COMMIT} (original, before any optimizations)
- **{METRIC_NAME}**: {BASELINE_METRIC_VALUE}
{BASELINE_SECONDARY_METRICS}

## Progress Log

Append a one-line entry here for every **kept** experiment. This log is committed with the code so you always see it when reading program.md. Format: `- {commit}: {description} → {metric_name} {value} ({percent_change}%)`

{PROGRESS_LOG_SEED}

## NEVER STOP

Once the experiment loop has begun (after the initial setup), do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep or away from the computer and expects you to continue working *indefinitely* until you are manually stopped. You are autonomous. If you run out of ideas, think harder — re-read the context files for new angles, try combining previous near-misses, try more radical changes, search for patterns in what worked vs what didn't in results.tsv and the Progress Log. The loop runs until the human interrupts you, period.
