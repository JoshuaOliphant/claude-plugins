# {PROJECT_NAME}

This is an experiment to have an LLM autonomously optimize {WHAT_IS_BEING_OPTIMIZED}.

## Setup

To set up a new experiment run, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar11`). The branch `autoloop/{tag}` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b autoloop/{tag}` from current main.
3. **Read the in-scope files**: Read these files for full context:
   - `README.md` — project context.
{IMMUTABLE_FILES_LIST}
   - `{MUTABLE_FILE}` — the file you modify. {MUTABLE_FILE_DESCRIPTION}.
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
- Install new packages or add dependencies.
- Modify the evaluation/metric extraction. {METRIC_NAME} is the ground truth.

**The goal is simple: get the {METRIC_DIRECTION} {METRIC_NAME}.** {ADDITIONAL_GOAL_CONTEXT}

**Resource constraints**: {RESOURCE_CONSTRAINTS}

**Simplicity criterion**: All else being equal, simpler is better. A small improvement that adds ugly complexity is not worth it. Conversely, removing something and getting equal or better results is a great outcome — that's a simplification win. When evaluating whether to keep a change, weigh the complexity cost against the improvement magnitude.

**The first run**: Your very first run should always be to establish the baseline, so run the command as-is without modifications.

## Output format

Once the execution step finishes, extract the key metric:

```bash
{METRIC_EXTRACTION_COMMAND}
```

Expected output format:
```
{METRIC_OUTPUT_EXAMPLE}
```

## Logging results

When an experiment is done, log it to `results.tsv` (tab-separated, NOT comma-separated).

The TSV has a header row and 4 columns:

```
commit	{METRIC_NAME}	status	description
```

1. git commit hash (short, 7 chars)
2. {METRIC_NAME} achieved — use 0 for crashes
3. status: `keep`, `discard`, or `crash`
4. short text description of what this experiment tried

Example:

```
commit	{METRIC_NAME}	status	description
a1b2c3d	{BASELINE_METRIC_VALUE}	keep	baseline
b2c3d4e	{IMPROVED_METRIC_EXAMPLE}	keep	{EXAMPLE_IMPROVEMENT_DESC}
c3d4e5f	{WORSE_METRIC_EXAMPLE}	discard	{EXAMPLE_DISCARD_DESC}
d4e5f6g	0	crash	{EXAMPLE_CRASH_DESC}
```

## The experiment loop

The experiment runs on a dedicated branch (e.g. `autoloop/mar11`).

LOOP FOREVER:

1. Look at the git state: the current branch/commit we're on.
2. Propose a change to `{MUTABLE_FILE}` based on your understanding of the domain, previous results in `results.tsv`, and ideas from the context files.
3. git commit the change.
4. Run the experiment: `{EXECUTION_COMMAND}` (redirect output — do NOT let it flood your context).
5. Extract the results: `{METRIC_EXTRACTION_COMMAND}`
6. If the extraction is empty or the command failed, the run crashed. Run `tail -n 50 {LOG_FILE}` to read the error and attempt a fix. If you can't fix it after a few attempts, give up on this idea.
7. Record the results in results.tsv (do NOT commit results.tsv — leave it untracked by git).
8. If {METRIC_NAME} improved ({METRIC_DIRECTION}), you "advance" the branch, keeping the git commit.
9. If {METRIC_NAME} is equal or worse, git reset back to where you started.

**Timeout**: Each experiment should take approximately {TIME_BUDGET}. If a run exceeds {TIMEOUT_LIMIT}, kill it and treat it as a failure (discard and revert).

**Crashes**: If a run crashes, use your judgment: If it's something simple to fix (typo, missing import), fix and re-run. If the idea is fundamentally broken, log "crash" and move on.

## Strategy guidance

{STRATEGY_GUIDANCE}

## NEVER STOP

Once the experiment loop has begun (after the initial setup), do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep or away from the computer and expects you to continue working *indefinitely* until you are manually stopped. You are autonomous. If you run out of ideas, think harder — re-read the context files for new angles, try combining previous near-misses, try more radical changes, search for patterns in what worked vs what didn't in results.tsv. The loop runs until the human interrupts you, period.
