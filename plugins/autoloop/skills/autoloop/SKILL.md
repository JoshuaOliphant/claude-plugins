---
name: autoloop
description: >
  MUST use when the user wants autonomous, iterative optimization — letting Claude run experiments
  unattended. Trigger: "autoloop", "autoresearch", "experiment loop", "hill-climbing", "optimize
  overnight", "karpathy loop", "let Claude optimize while I sleep", "automate trying different
  approaches", "set up a loop to improve this", "run experiments overnight", or any request for
  iterative improvement with a scalar metric. Generates program.md + immutable runner script
  (auto/run.sh) with tiered quality gates and
  structured METRIC output, ready to run with claude --dangerously-skip-permissions.
allowed-tools: [Read, Write, Glob, Grep, Bash, Agent]
---

# Autoloop — Autonomous Experiment Loop Generator

## Goal

Turn an LLM coding agent into an autonomous scientist. Generate a self-contained `program.md` + `auto/run.sh` that lets the agent loop forever — edit code, run experiment, parse metric, git commit (keep) or git reset (revert) — while the human walks away.

The skill's job is the **design thinking**: mapping an arbitrary project onto the seven essential components that make this loop work, then generating the files. Getting the components right is the difference between a loop that runs 126 experiments overnight and one that crashes after 3.

## Dependencies

### Tools

- **`autoloop:codebase-scout`** — Subagent that explores the project directory to identify build system, test commands, source files, and candidate metrics. Delegates via `Agent(subagent_type="autoloop:codebase-scout", model="haiku")`.
- **`git`** — Used for checkpoint/rollback (commit to keep, reset to revert). Must be available in the project.

### Connectors

- **Project build system** — Whatever runs the experiments (pytest, cargo, npm, go test, etc.). Detected by the codebase-scout.
- **`claude` CLI** — The generated loop runs via `claude --dangerously-skip-permissions -p "Read program.md and execute the loop protocol."`.

## Context

### The Seven Essential Components

Every autoloop maps onto these seven components. There is no orchestration code — `program.md` IS the entire system.

1. **Mutable artifact** — the one file the agent edits
2. **Immutable context** — files the agent reads but never touches
3. **Primary metric** — a single number that says "better" or "worse"
4. **Secondary metrics** — numbers tracked for tradeoff monitoring (not optimized, prevents Goodhart's Law)
5. **Runner script** — immutable shell script that runs quality gates and emits structured `METRIC` output
6. **Quality gates** — tiered checks (fast tests → conformance/lint → benchmark) that fail fast
7. **Checkpoint/rollback** — git commit to keep, git reset to revert

Plus a **results ledger** (`results.tsv`) and an **embedded progress log** (in `program.md` itself) that give the agent full history every iteration.

### Mutable Artifact Selection

| Goal | Likely mutable file |
|------|-------------------|
| ML training improvement | The training script (train.py, train.rs) |
| Test coverage | The source files being tested (pick the lowest-coverage one) |
| Performance | The module containing the hot path |
| Lint score | Source files with the most violations |
| Prompt engineering | The prompt template file |
| Config tuning | The config file being tuned |

The mutable file should be small enough for the agent to read in one pass. If >500 lines, suggest a focused subset or ask the user to extract the relevant section.

### Metric Inference

Check what the project already has:

| Project has... | Candidate metric |
|----------------|-----------------|
| Tests | Test count, coverage %, pass rate |
| Benchmarks | Execution time, throughput, ops/sec |
| Linting | Ruff/pylint issue count (lower is better) |
| ML training | Validation loss, accuracy, perplexity |
| Eval suite | Accuracy, F1, score |

Common secondary metrics by domain (guardrails, NOT optimized):

| Primary metric | Good secondary metrics |
|---------------|----------------------|
| Execution time (µs) | Allocations, memory usage, code complexity |
| Test coverage (%) | Test count, test execution time |
| Lint score | Lines of code, cyclomatic complexity |
| Validation loss | Training time, GPU memory, inference latency |
| Throughput (req/s) | P99 latency, error rate, CPU usage |

### Quality Gate Design

Gates run before the benchmark, ordered fastest-first. Early gate failure → immediate exit → no wasted benchmark time.

| Gate | Purpose | Failure mode | Example |
|------|---------|-------------|---------|
| **Unit tests** (fast) | Correctness | Hard fail (exit 1) | `uv run pytest tests/unit -x` |
| **Conformance/lint** | Style + spec | Soft fail with threshold | `ruff check --statistics`, allow ≤N issues |
| **Type check** | Type safety | Hard fail | `uv run mypy src/` |

Use what the project already has — don't add new tooling.

### Domain Strategies

For detailed allowed change types per domain (ML, test coverage, performance, lint, prompts, config tuning), consult:

→ **`references/domain-examples.md`**

## Process

### Step 0: Load Stored Feedback

Load any stored feedback preferences before starting:

```bash
python ${PLUGIN_ROOT}/scripts/feedback_manager.py autoloop show-feedback
```

If feedback entries exist, apply them throughout loop design:
- **loop_design** → adjust overall loop structure and iteration strategy
- **metrics** → guide metric selection and direction
- **quality_gates** → ensure preferred gates are included or excluded
- **runner_script** → adjust runner script generation
- **time_budget** → calibrate experiment duration and timeout settings
- **change_strategy** → shape allowed change types in program.md
- **general** → apply to all aspects of loop design

### Step 1: Scout the Project

Delegate to the codebase-scout agent:

```
Agent(
  subagent_type="autoloop:codebase-scout",
  model="haiku",
  prompt="Explore {cwd} and return a structured summary of: project type, language, build/test/bench commands, source files, config files, candidate metrics, and immutable files. See your instructions for the full output format.",
  description="Scout project for autoloop"
)
```

Tell the user: "I'm exploring your project to understand the build system, test infrastructure, and what metrics we can optimize. This takes about 15 seconds."

When results come back, summarize in 3-5 bullet points. Don't dump the raw output.

### Step 2: Design the Loop

Using the scout results AND the user's stated goal, design all seven components. Think carefully — wrong choices here waste hours of autonomous runtime.

**2a. Infer the mutable artifact** — Use the selection table from Context. If the answer isn't obvious, present 2-3 options with trade-offs.

**2b. Infer the metric** — Use the metric inference tables from Context. Determine the direction: "lowest" (minimize) or "highest" (maximize). Identify 1-3 secondary metrics as guardrails.

> **STOP if no metric can be inferred.** Do not guess. Ask the user: "I can see how to run experiments, but I can't determine what metric to optimize. What number should I be trying to improve? It needs to be something I can parse from command output."

**2c. Infer the execution command** — Usually comes directly from scout results. The command should redirect output to a log file: `{cmd} > run.log 2>&1`.

**2d. Design the time budget:**
- Fast tests (<30s): budget 1 min, timeout 3 min
- Medium tests (1-5 min): budget to match, timeout 2x
- Slow training (>5 min): budget to match, timeout 3x
- Very slow (>30 min): warn the user that fewer experiments will run overnight

**2e. Define files in scope and off limits** — Be specific with paths. "Don't touch tests" is vague; `test/**/*.py — test suite, must continue to pass unchanged` is clear.

**2f. Define allowed change types** — Read the appropriate domain block from `references/domain-examples.md`.

**2g. Design quality gates** — Use the gate design table from Context. For each gate, determine: command, failure mode (hard/soft), threshold (for soft fails).

### Human Checkpoint: Present the Design

Present the complete design as a single summary:

```
## Autoloop Design

**Goal**: {what we're optimizing}
**Mutable file**: `{path}` — {description}
**Primary metric**: {metric_name} ({units}, {direction} is better)
**Secondary metrics**: {name1} ({units}), {name2} ({units}) — tracked, not optimized
**Quality gates**:
  1. {gate1_name}: `{command}` — {hard/soft fail}
  2. {gate2_name}: `{command}` — {hard/soft fail, threshold if soft}
  3. Benchmark: `{bench_command}`
**Time budget**: ~{budget} per experiment (timeout: {timeout})
**Files in scope**: {list}
**Off limits**: {list}
**Strategy**: {domain} — {brief description of change types}

Does this look right? I'll adjust anything before generating.
```

**Wait for user confirmation before proceeding.**

### Step 3: Generate Runner Script and Verify Baseline

**3a. Generate `auto/run.sh`** — Read `references/runner-script-template.sh` and fill in quality gates + metric extraction from the design.

```bash
mkdir -p auto
```

The runner script structure:
1. Shebang + set flags: `#!/usr/bin/env bash` + `set -euo pipefail`
2. cd to project root: `cd "$(dirname "$0")/.."`
3. Quality gates in order (fastest first)
4. Benchmark: runs the metric-producing command
5. METRIC output: prints `METRIC key=value` lines

Make it executable: `chmod +x auto/run.sh`

**3b. Verify baseline** — Run the script once and check:

```bash
./auto/run.sh > run.log 2>&1
echo "Exit code: $?"
grep '^METRIC ' run.log
```

Verify: exit code 0, METRIC lines present, values reasonable (not NaN, not 0 when shouldn't be).

**Do not proceed to generation until the baseline passes.** If anything fails, debug it with the user.

Record the baseline commit hash: `git rev-parse --short HEAD`

### Step 4: Generate program.md

**4a. Read the template** — Read `references/program-md-template.md`.

**4b. Read domain strategy** — Read the appropriate section from `references/domain-examples.md`.

**4c. Fill variables** — Replace all `{VARIABLE}` placeholders with values from the design.

For the complete variable mapping, consult:

→ **`references/program-md-template.md`** (variables are documented inline)

### Human Checkpoint: Preview and Confirm

Show the user the generated program.md content:

> "Here's the program.md I'll write to your project root. Review it — once you confirm, I'll create the files."

**Wait for user confirmation before writing.**

On confirmation, write:
1. `program.md` to the project root
2. `results.tsv` with just the header row
3. Add `results.tsv` and `run.log` to `.gitignore` (append if exists, create if not, skip if already listed)

Do **NOT** git commit. Leave that to the user.

## Output

### Generated Files

| File | Purpose | Mutable by agent? |
|------|---------|-------------------|
| `auto/run.sh` | Quality gates + METRIC output | Never |
| `program.md` | Loop instructions + embedded progress log | Progress log only |
| `results.tsv` | Experiment ledger (append-only) | Append only, never committed |

### Launch Instructions

Print to the user after file generation:

```
## Ready to Launch

To start:

1. Review `auto/run.sh` and `program.md`.

2. Start the loop:
   claude --dangerously-skip-permissions -p "Read program.md and execute the loop protocol. Do not stop until I interrupt you."

3. Walk away. The agent will:
   - Create a branch (autoloop/{tag})
   - Establish baseline via ./auto/run.sh
   - Loop: edit → run → measure → keep/revert
   - Log every experiment to results.tsv
   - Update the Progress Log in program.md

4. When you come back:
   cat results.tsv                    # Full experiment trajectory
   grep '^- ' program.md | tail -20   # Progress log of kept changes
   git log --oneline                  # Which iterations were kept
   git diff main..HEAD               # Cumulative changes

5. If you like the results:
   git checkout main
   git merge autoloop/{tag}           # Or cherry-pick specific commits
```

### Troubleshooting

For common issues (agent stops early, every experiment crashes, metric not improving, etc.), consult:

→ **`references/troubleshooting.md`**
