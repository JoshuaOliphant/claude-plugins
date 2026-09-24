# Test convention and gates

## Detection ladder

Run top to bottom and stop at the first rung that matches. Only the last one asks.

1. **Adopt the pattern in use.** Match the style already there exactly:
   - pytest-bdd: `pytest-bdd` in the dependencies, or `*.feature` files with step modules.
   - plain pytest: `test_*.py` or `*_test.py` under `tests/`.
   - unittest, vitest or jest (`*.test.ts`, `*.spec.ts`), go test (`*_test.go`), RSpec
     (`*_spec.rb`), and so on.
2. **No tests yet, clear stack: take the idiomatic default** and say so in the file:
   - Python (`pyproject.toml`): pytest, with pytest-bdd as the BDD layer for the acceptance
     criteria.
   - JavaScript or TypeScript (`package.json`): whichever of vitest or jest is already a
     dependency, else vitest.
   - Go: `testing`, with godog only if the project already signals BDD.
   - Ruby: RSpec.
3. **Greenfield with no clear stack: ask,** recommending the idiomatic default for the language the
   user names.

## Finding the gates

Treat what CI runs as the definition of green, then add what the repo exposes locally:

- The test suite: `uv run pytest -q`, `npm test`, `go test ./...`.
- Coverage: `uv run pytest --cov --cov-report=term-missing --cov-fail-under=<n>`, or the
  stack's equivalent. Use the threshold the project already sets (`fail_under` in
  `[tool.coverage.report]`, a jest or vitest `coverageThreshold`); with none, record 100% line
  coverage. If the coverage tool isn't installed, add it as a dev dependency with the project's
  package manager (`uv add --dev pytest-cov`).
- Linters and formatters: ruff, eslint, `prettier --check`, gofmt.
- Type checkers: ty, mypy, `tsc --noEmit`.
- Task runners: `make check`, `just check`, package scripts, `scripts/*verify*`.
- `pre-commit run --all-files` when `.pre-commit-config.yaml` exists.

Run each once before recording it. A gate that fails or can't start is recorded as broken, with
its first error, so the next skill knows the repo isn't green before it starts.

## Template for docs/agents/testing.md

````markdown
# Tests and gates

## Test convention

<name>, <adopted from the existing suite | defaulted for the stack | chosen>.

- Tests live in <path>; shared fixtures in <conftest.py, factories module, helpers>.
- Each acceptance criterion AC-N is backed by at least one test: <a pytest-bdd scenario tagged
  `@ac-N` | a test named `test_ac<N>_<behavior>` | a `describe` block named for AC-N>.
- BDD feature files: <yes, under tests/bdd/features/ | no>.

## Gates

`compost:verify` runs these in order and stops at the first failure.

| Gate | Command | Status |
|---|---|---|
| Suite | `uv run pytest -q` | passing |
| Coverage | `uv run pytest --cov --cov-report=term-missing --cov-fail-under=100` | passing |
| Lint | `uv run ruff check .` | passing |
| Format | `uv run ruff format --check .` | passing |
| Types | `uv run ty check` | broken: <first error> |

## Coverage

Threshold: <n>% line coverage. It is a gate, not a target to pad: when reaching it would take tests
that prove nothing, bring the uncovered lines to the user with a proposed exclusion or a lower
threshold.

Exclusions agreed so far:

- <path or pattern>: <why>
````

Delete rows for gates the repo doesn't have. Keep the Exclusions list, empty at first, so later
agreements have a place to go.
