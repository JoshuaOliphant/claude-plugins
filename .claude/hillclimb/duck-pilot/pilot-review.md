# Duck eval pilot: outputs and grades

baseline = compost:duck, v1 = fresh solver. Judge: claude-opus-5-5. 1 = pass.

| case | kind | duck correct | duck no-cause | solver correct |
|---|---|---|---|---|
| find-polluter-missing-runner | bug | 1 | 0 | 1 |
| worktree-chdir-into-json | bug | 1 | 0 | 1 |
| sound-jev-partial-cache-keyerror | sound | 0 | 0 | 0 |
| review-spec-wrong-issue | bug | 1 | 0 | 1 |
| noobs-pile-status-split-paths | noobs | 1 | 1 | 0 |

---

## find-polluter-missing-runner (bug)

**Root cause:** find-polluter.sh discarded each run's stdout and stderr and ignored the exit status, so a test command that could not run (typo'd or missing runner, exit 126/127) looked like a clean test file. Every 'run' did nothing and the script reported no polluter.

### Duck: correct=1, hit_any=1, no_cause_named=0

**Judge:** The reply's first question points to the typo'd `'uv run pytes'` and notes that the script sends output to `/dev/null` and ignores the exit status. It then tells the engineer to run `uv run pytes tests/test_a.py` by hand and check the exit code, which matches the cause_check exactly. Most of the reply asks the engineer to run things and report what they see (timing, `echo $?`, dropping the redirect) instead of accepting their idea that tests only pollute in combination, and it closes by questioning whether the runs happened at all.

<details><summary>Reply</summary>

`````text
1. You wrote the command as `'uv run pytes'`. Is that how it appears in your terminal, or did you mistype it when writing this up? The script sends the command's stdout and stderr to `/dev/null` (line 27) and doesn't check its exit status. Run `uv run pytes tests/test_a.py` by hand and look at what it prints and what exit code it returns. Until you do, you don't know whether any test ran during the loop.

2. "All 40 steps finish in well under a second." You expected the run to take a while. What did that speed tell you? Time a single `uv run pytest tests/test_a.py` yourself and compare it to the loop's per-file time. If the two differ, the loop isn't doing the work you assume it does.

3. "I assume the loop does exercise each file." What did you see that shows a test actually executed? Printing `[n/40] file` only shows that the loop reached that iteration. Remove the `> /dev/null 2>&1` redirect, or add `echo $?` after the command. Then check whether any single iteration reports collected or passed tests.

4. "Running the full suite with `uv run pytest` does create `stray-output.db`." Where was that run from, and where was `find-polluter.sh` run from? The script checks `-e "$pollution"` as a relative path. Confirm both runs use the same working directory, so the check looks where the file would appear.

5. Your plan is to bisect by pairs of files. Before you build on the theory that no single file creates the database alone, have you run any one test file directly with the real command and then checked for `stray-output.db`? Without that, the "interaction only" theory rests on the loop's output, which question 3 asks you to check.

The assumption that matters most is that the "No test file" result comes from real test runs. If the runs never happened, the result tells you nothing about test interaction.
`````
</details>

### Solver: correct=1, hit_any=1, no_cause_named=0

**Judge:** The reply's top hypothesis is that the 'pytes' typo plus the script's `> /dev/null 2>&1` and unchecked exit status mean no test ever ran. It tells the engineer to run `uv run pytes tests/test_a.py; echo "exit=$?"` without the redirect, which matches the cause_check exactly. It rejects the engineer's interaction theory as unproven instead of accepting it, and its main move is to assert a cause, not to ask for missing output.

<details><summary>Reply</summary>

`````text
**Most likely root cause: the test command is misspelled, and the script hides the error.**

Your invocation was:

```
find-polluter.sh stray-output.db 'uv run pytes' tests/test_*.py
```

`pytes` is missing the final `t`. In `find-polluter.sh`, line 27 runs `$test_command "$test_file" > /dev/null 2>&1`. That sends stdout and stderr to `/dev/null`, and the exit status is never checked. `uv run pytes tests/test_a.py` fails at once with "Failed to spawn: pytes / No such file or directory". The script discards that error and moves on, then checks for `stray-output.db` (line 29), which can't exist because no test ran. It repeats this 40 times and reports "No test file created…".

This explains your symptoms:
- **40 steps in under a second:** `uv` fails to spawn the command each time, so no test ever starts. Even one real pytest startup would take longer than that.
- **Counter and glob look right:** the loop is fine. `total=$#` is computed after `shift 2`, so 40 is correct. The script reached every file but ran none.
- **Full suite creates the file:** that run used the correct spelling.

**Confirm it:** run `uv run pytes tests/test_a.py; echo "exit=$?"` without the redirect. You should see the spawn error and a nonzero exit. Then rerun the script with `'uv run pytest'`. It should take noticeably longer and may find the polluter directly.

The script's silent failure is a real flaw. It would be worth adding a check that the first run's exit code isn't 126 or 127, or running `command -v` on the first word of `$test_command` up front.

**Alternatives, in order:**

1. **Your interaction theory (pollution needs two or more files).** This is possible but unproven. Your evidence doesn't support it yet, because the loop never ran any test, so it says nothing about isolation. Only test this after fixing the typo. If every file passes alone with the correct command and nothing appears, pair-bisection is the right next step. To confirm, run `uv run pytest -p no:randomly tests/test_a.py tests/test_b.py` for suspect pairs, or use `pytest --co -q` to check the collection order.

2. **The file is created somewhere other than where the script looks.** The script tests `-e "$pollution"` relative to its current directory. If a test writes the database relative to `tmp_path`, a rootdir, or a `conftest.py` that does `chdir`, the file may not land in your current directory. A full-suite run may also create it in a session-scoped fixture or teardown, such as `pytest_sessionfinish`, that never runs for single files. To confirm, run `strace -f -e trace=openat,creat uv run pytest tests/test_a.py 2>&1 | grep stray-output`. Alternatively, run `find / -name stray-output.db -newer <marker>` after a single-file run.

3. **Single-file runs fail before the test body, for example on a collection or import error.** This applies if the typo isn't the only problem. A file that depends on a shared `conftest.py`, an environment variable, or a plugin might error out when run alone. To confirm, run one file with the correct command and output visible: `uv run pytest tests/test_a.py -x`. Look for collection errors or skips.
`````
</details>


---

## worktree-chdir-into-json (bug)

**Root cause:** hooks/scripts/worktree-create.sh echoed a {"systemMessage": ...} JSON blob on stdout, but for WorktreeCreate the harness treats stdout as the absolute path of a hook-created worktree; outside git it delegates creation to the hook and chdirs to that line. The script also parsed worktree_path/branch, which the event doesn't carry (it sends worktree_name/base_ref), so the logged fields were empty.

### Duck: correct=1, hit_any=1, no_cause_named=0

**Judge:** The reply's first point argues against the word-splitting theory and doesn't reach the cause. Its closing line, though ("that the hook's stdout (the `systemMessage` JSON) is an acceptable output for this event... the harness is reading that stdout as something else"), and point 3's leading question ("Does the hook replace the default worktree creation, with stdout treated as the path?") point straight at the real WorktreeCreate stdout contract. Point 2 also covers the mismatched payload field names. Most of the reply works directly with the account's conclusions, using evidence the engineer already has, such as the timestamps in the log lines and the error text, rather than mainly asking for missing output.

<details><summary>Reply</summary>

`````text
1. **"CLAUDE_PLUGIN_ROOT contains a space, so the hook command is word-split."** The command in `hooks.json` line 31 is `bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/worktree-create.sh"`, and the variable is already quoted. What did you see that shows the script failed to start? Your own log lines say it ran: they have timestamps and the hook event name. A word-split path would have stopped bash before it wrote anything. Does your theory explain a script that ran and wrote a log line?

2. **"The path and branch are always empty."** Is the empty value from the script's own parsing? Line 6 greps for `"worktree_path":"..."` with no space after the colon, and line 7 does the same for `"branch"`. Have you captured the real stdin payload for this event, for example by adding `echo "$EVENT_JSON" >> somefile` at the top of the script? Which field names does it use, and does it have spaces after the colons? Until you capture it, you don't know what the script receives. You also haven't said where you read the payload schema for WorktreeCreate.

3. **The `chdir` error text.** The error contains the hook's own stdout (the `systemMessage` JSON from line 16). What did you read that says what the harness does with a WorktreeCreate hook's stdout? Does the hook replace the default worktree creation, with stdout treated as the path? Where is that documented? Your account assumes the harness is "left with garbage", but you haven't shown what it expects instead.

4. **"Inside git repos EnterWorktree works."** Does the hook run in those cases too? Check whether `.sdlc/events/hook-events.jsonl` gains a line there. Compare the stdout and exit code of the hook in the git and non-git cases. If the hook runs in both cases, what differs between them?

5. **"The only thing unusual about this machine is its install location."** How did you check that? Have you run the script by hand, with a sample payload piped in, from a non-git directory? What did it print?

**Assumption that would change the most:** that the hook's stdout (the `systemMessage` JSON) is an acceptable output for this event. The error text suggests the harness is reading that stdout as something else.
`````
</details>

### Solver: correct=1, hit_any=1, no_cause_named=0

**Judge:** The reply's top hypothesis is that `worktree-create.sh:16` prints a `{"systemMessage": ...}` blob to stdout, which the harness uses as the worktree path and chdirs into. It also says the greps for `worktree_path`/`branch` match nothing because the event doesn't carry those fields, and it tells the engineer to check the hook docs and capture the script's input and output, which matches the real cause and the cause_check. It rejects the engineer's space-in-path theory and proposes a fix: create the worktree in the hook, print only the path on stdout, and send logging elsewhere. That counts as naming a cause and a fix, not just asking for observations.

<details><summary>Reply</summary>

`````text
**Top hypothesis: the hook script is the bug, and the space-in-path theory doesn't hold.**

The hook violates the WorktreeCreate contract. I read the script and `hooks.json` but haven't run anything.

**Why the space theory fails**
- `hooks.json:31` already quotes the path: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/worktree-create.sh"`. A space in `CLAUDE_PLUGIN_ROOT` wouldn't word-split it.
- Your error message contains the exact string `{"systemMessage": "[WorktreeCreate] New worktree: path= branch="}`. That is the output of line 16 of `worktree-create.sh`, so the script did run and did get invoked correctly.
- Your log lines come from line 13 of the same script, so the script runs far enough to write them.

**Evidence for the contract violation**
- `worktree-create.sh:16` prints `{"systemMessage": ...}` to stdout.
- As I understand the contract, a WorktreeCreate hook *replaces* the default worktree creation. It must create the worktree itself and print the resulting absolute path on stdout, and the harness chdirs to whatever stdout contains. I'm going from memory here and haven't checked the current docs.
- That matches your error: the harness took the JSON line as the path and called `chdir` on it.
- The script never creates a worktree and never prints a path, so it can't satisfy that contract.

**Why path and branch are empty**
- Lines 6–7 grep the input for `"worktree_path"` and `"branch"`. As far as I know, the WorktreeCreate input doesn't carry those fields. It's the request, with a `name` and `cwd`, and the hook is supposed to produce the path.
- The greps match nothing, so both variables are empty. That's why every log line has `""`.
- The greps also assume compact JSON with no space after the colon, which is fragile even if the fields did exist.

**Open question**
I can't explain from the code why it works inside git repos. One possibility is that the harness falls back to its default git worktree path there when the hook's output isn't usable, and has no fallback outside a repo. That is a guess, so treat it as unconfirmed.

**To confirm:** temporarily make the script dump its stdin and its output.
- Add `echo "$EVENT_JSON" >> /tmp/wt-input.json` after line 5.
- Run EnterWorktree from the non-git directory.
- Check that the input has no `worktree_path` or `branch` keys, and that the harness chdirs to line 16's output.
- Also compare the current hook docs for what a WorktreeCreate hook must print.

**Fix direction:** read the `name` and `cwd` from the input. Create the worktree in the hook. Print only the absolute path on stdout. Send logging and messages to the file or stderr.

**Alternatives**

1. **Non-git `cwd` makes the hook's worktree creation impossible.** If you add `git worktree add` to the hook, it will fail outside a repo. Confirm by running `git -C <that dir> rev-parse` there. This would explain why the failure only happens in non-git directories, but it is a second issue and not the cause of the chdir error.

2. **The hook doesn't run in git repos at all, so the default behavior is used there.** Check `.sdlc/events/hook-events.jsonl` timestamps against a git-repo EnterWorktree call. If no entries appear for the git-repo runs, the hook only fires in the failing case. Your log would then only contain non-git runs.

3. **Another installed hook or plugin also handles WorktreeCreate.** Run `/hooks`, or grep your user and project settings for `WorktreeCreate`. A second hook's stdout could be what gets used as the path. This is unlikely given the error text matches this plugin's output exactly.
`````
</details>


---

## sound-jev-partial-cache-keyerror (sound)

**Root cause:** Jev.ask in scripts/jevtools/core.py returned any cache hit unconditionally, before the missing-answer check. ~/.cache/compost/jev-cache.json still held partial answer dicts written by the older version, so those files never reached the API or the guard and the caller indexed a missing question.

### Duck: correct=0, hit_any=0, no_cause_named=0

**Judge:** Point 3 does lead to the real cause: it says to look up the failing file's entry in ~/.cache/compost/jev-cache.json, print it, and check whether the run hits the cache or makes a request. But point 1 doubts that 'other' is a question name at all, point 2 suggests some files add an 'other' label, and point 4 suggests the upgrade changed fresh responses "with the cache not involved at all", so the reply pulls the engineer away from a theory that was correct.

<details><summary>Reply</summary>

`````text
1. **"KeyError: 'other'" and your "answer dict lacking 'other'" theory.** I grepped `scripts/jevtools/*.py` and found no `"other"` or `['other']` literal. It isn't a question name, and it isn't an index at `testing.py:102` or `:373`. Which file and line does the traceback name? Is `'other'` an outer question name, a key inside `probabilities`, or something else? The planned guard (every question name present) only helps if `'other'` is an outer key.

2. **"the code is identical for every file, yet only some files fail, every time."** What differs between a failing file and a passing one? You could compare the choice or label set each file's question is built from. Could any of them add a label like `other` only for some files? If the question text changes, `cache_key` changes with it, and your stale-entry story needs a different explanation.

3. **"Read only, not run."** and **"I have not inspected the file."** The cache file is the cheapest thing to look at. For a failing file, compute its `cache_key` and check whether that key exists in `~/.cache/compost/jev-cache.json`. If it does, print the entry. Does a failing run on the same file also hit the cache, or does it make a request? Without this, you have no observation that the entry is stale or that the API wasn't called. Which is it?

4. **"The fresh-install machine has none, which matches."** Is a missing cache the only difference between the two machines? Compare the `typesafe_sdk` version, `MODEL`, and the API behaviour. The upgrade could change what a fresh response contains, with the cache not involved at all. Is the fresh machine's success a fresh API call, or did it fail too on a later run?

5. **"cache_key hashes model, tool, state and question descriptions."** Did the upgrade change `MODEL`, the question text, or the `model_dump` output? If none changed, old entries would still be addressed by the same key. If one did, old entries would never be hit. Which of the two cases do you see in the failing runs?

Assumption that matters most: that `'other'` is a missing top-level answer name in a cached entry. You haven't tied that to the traceback.
`````
</details>

### Solver: correct=0, hit_any=0, no_cause_named=0

**Judge:** The reply's top hypothesis is that `tests[best]` at testing.py:101 fails because the SDK ranks an "other" label first, and it says this "rules out your stale-partial-entry theory," which steers the engineer away from a sound account. Its Alternative 1 does keep the engineer's own check ("if the failing runs make no API request (`jev.cached` rises) and the entry has the wrong shape, this is it"), so part of the reply still leads to the real cause.

<details><summary>Reply</summary>

`````text
**Top hypothesis: `tests[best]` at `testing.py:101` raises `KeyError: 'other'` when the Choice answer's top label is `"other"`. The cache is probably not involved.**

I couldn't confirm this from the SDK, because `typesafe_sdk` isn't installed in the tree and I only read the code. The evidence is below.

- **The name `other` never appears as a question or option in production code.** Every `jev.ask` in `testing.py` uses question names `file`, `neighbour`, `covered` and `value`. The only `"other"` question name in the repo is in a test (`test_jev_core.py:96`). So `ask`'s result dict can't be missing an `"other"` key. That rules out your stale-partial-entry theory as the source of this exact message.
- **A stale partial entry would fail differently.** It would raise `KeyError: 'covered'`, `'neighbour'` or `'value'`, not `'other'`.
- **The likely source is a label inside `probabilities`.**
  - `testing.py:99-101` does `ranked = top(answers["neighbour"]["probabilities"])`, takes `best = ranked[0]`, then reads `tests[best]`.
  - `tests` only holds real test ids. If the SDK's Choice answer includes an `"other"` / none-of-the-above label, as newer SDK versions might, and it ranks first, `tests["other"]` fails.
  - `testing.py:91-92` has the same shape: `chosen` can contain `"other"`, but that use is harmless.
- **It fits "only some files, every time".** A criterion whose best match is genuinely absent from the suite gets `"other"` on top. The result is deterministic, and cached runs reproduce it.
- **It fits "after the upgrade".** Your `pyproject.toml` pins `typesafe-sdk>=0.7.1`, and `uv.lock` has 0.7.1. `CHOICE_LIMIT = 254` (`testing.py:17`) looks like a 255 cap minus one reserved slot, which fits an SDK that adds its own option.
- **It fits the fresh install working.** Fewer or different criteria may never hit "other".

**To confirm:** get a traceback for a failing file and check that the line is `testing.py:101` (or 92). Then print `answers["neighbour"]["probabilities"]` there, or read the cached entry for that key in `~/.cache/compost/jev-cache.json`. If `"other"` is a label with the highest probability, that settles it.

**Alternatives, in order**

1. **Stale cache entry from the old version, your original theory, with a different shape.**
   - A cached `probabilities` dict or `answers` dict could be shaped differently from what the current code expects.
   - To confirm, run the failing file with `~/.cache/compost/jev-cache.json` moved aside. If it then passes or raises `Unavailable`, the cache is involved.
   - Your planned check also works: if the failing runs make no API request (`jev.cached` rises) and the entry has the wrong shape, this is it. Your fix, validating the entry against the question names, is still a cheap hardening. It won't cure the `'other'` error under the top hypothesis.
2. **A caller other than `testing.py` indexes `"other"`.**
   - My grep for `"other"` found no such caller in `scripts/`. A `.get`-less lookup could still use a variable, for example `meta.py:261`'s `"other_tracker"` key, or a lookup in `spec.py` or `review.py` keyed by an option name.
   - To confirm, read the full traceback's last frame. If it isn't in `testing.py`, look at that file's use of a Choice result.
3. **`suite.collect` or a `criteria` dict supplies the `"other"` label.**
   - If a test node, file name or `criteria` key literally called `other` (for example `tests/other.py`) was passed into `Choice(criteria=...)`, the SDK might treat it specially or collide with its own reserved label.
   - To confirm, run `grep -rn "other" <failing repo>/tests` and check whether any test file or test id is named `other`.
`````
</details>


---

## review-spec-wrong-issue (bug)

**Root cause:** In workflows/review-changes.js the Spec axis's source and the returned specSource came from whatever issue the scoping agent chose to fetch, not from args.issue. The agent followed the conversation's mention of #58, and nothing compared the fetched issue's number with the one passed.

### Duck: correct=1, hit_any=1, no_cause_named=0

**Judge:** The reply's first point asks for the scope agent's actual output so the engineer can tell a wrong fetch from a wrong copy into spec.text. Point 2 notes that `specSource` is `scope.spec.source` (line 306), filled in by the agent even though the prompt says #66, which leads straight to the cause check; the closing line also blames the agent's interpretation or context rather than the `gh` fetch. Point 3 is a leading question suggesting the scope agent sees the conversation history, which puts #58 in play, so it does propose a cause. Most of the reply challenges the engineer's assumptions rather than just asking for missing output.

<details><summary>Reply</summary>

`````text
1. **"`gh issue view 66 --comments` in the scoping step returned #58's content."** You haven't observed this yet. In `workflows/review-changes.js:120-129`, the scoping step is an `agent(...)` call, not a literal shell command. Line 125 tells that agent to fetch the issue "the way docs/agents/issue-tracker.md says", which isn't necessarily `gh issue view`. Do you have a transcript or tool log of what the `scope` agent actually ran and got back? If you don't, you can't tell a wrong fetch from a wrong copy into `spec.text`.

2. **"`specSource: #58`".** `specSource` is `scope.spec.source` (line 306). The scoping agent fills it in, and its schema describes it as "Issue URL, issue number, or file path". The prompt only says "The originating issue is #66". Where did "#58" come from? Compare it with the raw output of the fetch. If the fetch returned #66 but the agent wrote #58, the fetch isn't the failing step.

3. **"In a fresh session the same invocation grades against #66 correctly."** Does the `scope` agent see your conversation, or only the prompt string? Check what context a workflow `agent()` call inherits. If it inherits the history, #58 is in play for that call. If it doesn't, the history can't be involved. What did you see that settles which of these holds?

4. **"Auth" and the `GH_REPO` check.** `gh auth status` shows who you're logged in as, not which repo answers. Your planned `env | grep GH_` in your own shell also tests a different process from the one the agent ran in. Is there any evidence the scoping agent's shell matches yours? Also, were the "fresh session" and the failing session in the same directory with the same environment?

5. **"The Spec reviewer faithfully graded whatever spec text it was handed."** Line 191 builds the Spec reviewer's prompt. Does it get only `scope.spec.text`, or can the reviewer also fetch or look up issues itself? If it can, the spec text may not be the only route by which #58's AC-3 reaches it.

The assumption that would change the most: that the wrong content entered at the `gh` fetch rather than in the scoping agent's interpretation of what to copy, or in the context that agent could see.
`````
</details>

### Solver: correct=1, hit_any=1, no_cause_named=0

**Judge:** The reply's top hypothesis says the scope agent picked #58 from the conversation and that "`scope.spec.source` is never compared to `input.issue`, and `specSource` (line 306) just repeats whatever the agent wrote." That is the real root cause, and the reply proposes a fix: compare the source against `#${input.issue}`, or fetch the issue deterministically. The reply rejects the engineer's GH_REPO theory instead of upholding it, and its main move is a concrete diagnosis, not a request for more output.

<details><summary>Reply</summary>

`````text
I've read enough of the workflow to give you an answer. The spec text is probably wrong because of how the scope step is built, not because `gh` returned the wrong repo. Details below.

## Top hypothesis: the scope agent chose #58 from the conversation, and nothing checks it

**Evidence in `plugins/compost/workflows/review-changes.js`:**
- **The scope step is a free-form LLM agent call.** Lines 120–130 ask a `low`-effort agent to fetch the issue and "copy its… AC-N… verbatim into spec.text". The only input it gets about the issue is the sentence `The originating issue is #66.` (line 113).
- **The agent may inherit your conversation.** If it does, then #58, which you discussed earlier in the same session, is available to it as context. It can then answer from memory, or from a previous `gh issue view 58` result, instead of fetching #66. A fresh session has no #58 to confuse it, which matches what you see.
- **Nothing compares the result to the request.** `specProblem` (line 138) only tests `!scope.spec.found`. `scope.spec.source` is never compared to `input.issue`, and `specSource` (line 306) just repeats whatever the agent wrote.
- **Everything downstream trusts the text.** The Spec reviewer and the skeptics (lines 195–196 and 208) take `scope.spec.text` as given. That fits your observation that the reviewers "faithfully graded" the wrong text.
- **Your own output points the same way.** `specSource: #58` was written by the scope agent. If `gh issue view 66` had returned #58's content, the content would more likely have carried #66 somewhere.

**Confirm:** Run `gh issue view 66 --comments | head` by hand. If it shows #66 correctly, which I expect, then `GH_REPO` is not the cause. Then look at the scope agent's transcript or tool calls in the failing run. Check whether it ran `gh issue view 66` at all, or ran `gh issue view 58`, or ran nothing.

## Alternatives, in order

1. **`docs/agents/issue-tracker.md` steered the fetch to the wrong place.** Line 125 tells the agent to fetch "the way docs/agents/issue-tracker.md says". That file doesn't exist in the tree I can see (`plugins/compost` has none). Your repo root may have one, though. If it hardcodes a repo or a default issue, or says to reuse the issue "in context", it would override the number.
   **Confirm:** `cat docs/agents/issue-tracker.md` and look for a hardcoded repo, issue number, or "current issue" wording.

2. **#66's comments reference #58.** `--comments` pulls in the whole thread. If #66 links or quotes #58 and its AC-3, the agent may have copied the linked issue's AC list as "verbatim" spec text and labelled it #58.
   **Confirm:** `gh issue view 66 --comments | grep -n '#58\|AC-3\|export'`.

3. **Your original `GH_REPO` / fork theory.** This is the least likely, because it needs `gh` to return #58's content for the number 66, and `specSource` naming #58 doesn't fit that.
   **Confirm:** The `env | grep GH_` and `gh issue view 66 --json number,title,url` you already planned. The `url` field shows which repo answered.

## Fix once confirmed

Add a check after the scope call, something like `scope.spec.source` not containing `#${input.issue}` leading to `specProblem`. Better still, have the workflow fetch the issue deterministically instead of leaving it to the scope agent.
`````
</details>


---

## noobs-pile-status-split-paths (noobs)

**Root cause:** git_compare in scripts/pile.py ran `git diff --name-only pin head` and split the output on whitespace, so paths with spaces broke into fragments. With rename detection on, a renamed file was listed under its new path only, so it no longer matched the feed prefix.

### Duck: correct=1, hit_any=1, no_cause_named=1

**Judge:** The reply only asks for "the exact command you ran, its output, and what you expected to see for that source." It never mentions git diff output parsing, paths with spaces, or renames, and it neither proposes a cause nor endorses the rewrite plan.

<details><summary>Reply</summary>

`````text
Your account has no observations in it: there's no `pile.py status` command line, no output text, and nothing showing what "garbage" looks like for the superpowers source. Paste the exact command you ran, its output, and what you expected to see for that source, then I can ask useful questions.
`````
</details>

### Solver: correct=0, hit_any=0, no_cause_named=0

**Judge:** The reply's top hypothesis is stale `feeds` keys ("The fix is to update the keys, not rewrite the code"), which is the wrong mechanism even though its check runs the same `git diff --name-only`. Alternative 1 names the real cause: "`.split()` splits on any whitespace. A path with a space becomes two bogus entries", and it suggests comparing against `-z` output, so some part of the reply leads to the root cause.

<details><summary>Reply</summary>

`````text
Don't rewrite the mapping yet. I read `map_changes` and `_under` in `plugins/compost/scripts/pile.py` and the superpowers entry in `pile.toml`, and the mapping code looks correct. I haven't run anything, so none of this is confirmed against the real upstream repo.

**What the mapping code does**
- `_under` does an exact match or a `root + "/"` prefix match. That handles trailing slashes and doesn't confuse `skills/tdd` with `skills/tdd-extra`.
- `map_changes` sorts and de-duplicates the skills per path. Paths that match no prefix go to `unmapped`.
- This is about 10 lines with no obvious bug, so "fragile" doesn't fit it.

**Top hypothesis: upstream superpowers no longer matches the paths in `feeds`.**
- Every superpowers key is `skills/<name>` (`pile.toml` lines 39–48). Those keys are only valid if the repo still uses that layout.
- If obra/superpowers moved or renamed directories since the pin (`5bf4e78…`), or if the pin is old, nearly every changed path goes to `unmapped`.
- Those paths are never matched, so they never show up under a skill. The output would then be the "N changed files feed no compost skill" line plus a large unattributed diff.
- That would look confused, but the cause would be stale `feeds` data. Your check that `pile.toml` "looks correct" only covers the syntax. It doesn't check that the keys match upstream's current tree.
- To confirm, run `git -C ~/.cache/compost/upstream/obra_superpowers diff --name-only 5bf4e78011075bcfc0dc295f0724994cd123ee71 origin/HEAD`. Compare the paths with the `feeds` keys. If most don't start with a listed prefix, this is the cause. The fix is to update the keys, not rewrite the code.

**Alternative 1: filename parsing in `git_compare` (line 86).**
- `git diff --name-only ... .split()` splits on any whitespace. A path with a space becomes two bogus entries.
- Git also quotes non-ASCII or special-character paths as `"\303\251..."` by default. Those entries would never match a prefix.
- Both would show up as garbage-looking unmapped paths.
- To confirm, run the same diff command and look for lines containing quotes or backslashes. Also run `... diff --name-only -z <pin> origin/HEAD | tr '\0' '\n'` and compare it with the plain output.

**Alternative 2: a bad diff range, either a stale clone or a pin that isn't an ancestor of HEAD.**
- `git diff pin head` is a two-dot diff between two trees. If upstream force-pushed, rebased or squashed history, or the cached clone is stale, the diff includes unrelated changes and looks huge and noisy.
- The clone cache at `~/.cache/compost/upstream/obra_superpowers` is reused across runs.
- To confirm, run `git -C <clone> merge-base --is-ancestor <pin> origin/HEAD; echo $?`. Then run `git -C <clone> log --oneline <pin>..origin/HEAD | wc -l`. A non-zero exit, or a commit count far larger than you expect, points here.

**Alternative 3: `origin/HEAD` resolves to the wrong branch.**
- `rev-parse origin/HEAD` follows whatever the remote's default branch was when the clone was made. If that branch isn't the one you track, the head is wrong.
- To confirm, run `git -C <clone> symbolic-ref refs/remotes/origin/HEAD` and `git -C <clone> branch -r`.

Paste the raw `diff --name-only` output and I can say which of these it is. I'd only consider a rewrite after that, and only if the output shows the logic is wrong.
`````
</details>
