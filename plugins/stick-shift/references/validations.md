# Validations: detect and use what the project and user already have

`/verify` proves the acceptance criteria in code (see `test-conventions.md`). Beyond that,
it should use whatever *other* verification the project and the installed skills offer —
detected, not hardcoded. The aim is a gentle nudge to apply the checks pertinent to the
actual code changes, not to run a fixed list.

## Project-defined correctness gates — detect and run

These exist to be run; run the ones present and report real results:
- Test suite (already): `uv run pytest -q`, `npm test`, `go test ./...`, etc.
- Linters / formatters: ruff, eslint, `prettier --check`, gofmt.
- Type checkers: `ty`, mypy, `tsc --noEmit`.
- Task runners: `make check` / `make lint`, `just check`, `Taskfile` targets.
- `scripts/*verify*.sh` or similar project scripts.
- `pre-commit run --all-files` if a `.pre-commit-config.yaml` exists.
- `package.json` scripts (`npm run lint`, `npm run typecheck`).
- Treat the project's CI commands (`.github/workflows/*`) as the definition of "green".

## Verification skills — use what's pertinent (decide-log-proceed)

Use the installed review/quality skills relevant to *these* changes without asking first;
log what you ran with `note-progress`. Bring something to the user only when it genuinely
needs their call (an ambiguous finding, a security judgment).
- `/code-review` (built-in) — correctness/bug review of the diff; apply trivial fixes.
- `vet` (if installed) — reviews the diff (and conversation) for issues.
- `security-review` (built-in) — when the change touches auth, secrets, input handling,
  or other security surface.
- `/simplify` (built-in) — **mutates code**; use only after compliance is green, then
  re-run the gates above. If it broke something, revert it rather than debugging it.

Pick by pertinence: a pure-logic change usually wants code-review/vet; a security-touching
change adds security-review; a noisy diff may warrant simplify + re-verify. Skip skills
that aren't installed, silently.
