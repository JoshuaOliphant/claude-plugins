# The proof ladder and silent checks

Depth for steps 5 and 6 of `compost:verify`.

## One fact, five rungs

Take the change from `compost:build`'s worked example: `authorize` drops its 60-second grace
period, so a token is refused at its expiry instant. The tests prove `authorize` does that. The
change is only safe because of a fact outside `authorize`:

> Clients never present a token within seconds of its expiry, because the issuer hands out tokens
> that live an hour and clients refresh them five minutes early.

That fact moves down the ladder like this:

1. **Asserted.** "Clients refresh early." A sentence, which reads the same whether it is true or not.
2. **Cited.** `issuer.py:31` sets `expires_in=timedelta(hours=1)`; the client SDK's
   `session.py:88` refreshes when `expires_at - now < timedelta(minutes=5)`. Cite the SDK at the
   version the clients actually pin, not the latest release.
3. **Walked.** Follow a request whose token is 4 minutes from expiry: the SDK refreshes before
   sending, so the server sees a token with 60 minutes left. Then look for the case the walk
   misses: a client whose clock runs 6 minutes slow refreshes too late. Clock skew is where grep
   stops.
4. **Ran.** A script that imports the real issuer and the real SDK, freezes the client's clock 6
   minutes behind the server's, makes a request, and asserts that the SDK refreshed first. If it
   fails, the fact is false and the grace period was covering for skew. The change then needs a
   decision, not a merge.
5. **Reproduced live.** Start the app with the bundled `/run`, log in, shift the client clock,
   and watch the request log for a refresh followed by a 200.

Stop at the cheapest rung that settles the fact, and report where you stopped. Below rung 4, the
fact is unproven. Say so in the report and in the PR's Risk section.

## Where grep stops

A symbol search finds callers. It does not find:

- the library's own behavior at the version in the lockfile, or a local patch to it
- data shapes crossing a process boundary: JSON from an API, a database column, a queue message,
  a file another program reads
- a feature flag or config value that selects the old path at runtime
- code reaching the symbol by string: `getattr`, entry points, templates, serializers
- timing: teardown order, retries, clock skew, a cache that outlives a deploy

## Silent checks

Each of these passes without doing the work you think it does. Next to each is the proof that it
ran.

| Check | How it passes silently | Proof it ran |
|---|---|---|
| `pytest -k <expr>` | The expression matches nothing: exit code 5, and the summary says only "8 deselected" | The collected count in the summary is the number you expect |
| pytest overall | Tests skipped by a missing optional dependency or a `skipif` | `-rs` lists skips; count them against the AC table |
| coverage | `source` names the wrong package, or the installed copy is measured instead of `src/` | The report lists the files the diff touched |
| ruff, mypy, ty | An `exclude` or `include` setting leaves the changed path out | `ruff check --show-files` or the checker's file count includes the changed files |
| pre-commit hook | Its `files:` pattern misses the changed files and it reports "Skipped" | The hook's line shows "Passed", not "(no files to check)Skipped" |
| a shell pipeline | `cmd \| grep x` exits with the status of `grep` | `set -o pipefail`, or check `cmd`'s own exit code |
| a hook or CI step | It never triggered for this path or event | Its own log line for this run |
| editing then re-running Python | An edit of the same size in the same second can leave stale bytecode running | `PYTHONDONTWRITEBYTECODE=1`, or clear `__pycache__` between runs |

When nothing on this list fits, plant a defect: break the line the check protects, run the
check, see it fail, and restore the line. One red run proves the check can see the failure.
