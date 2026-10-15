---
name: triage
description: >-
  Triages a superfan finding with the user: shows the evidence, checks whether it is still
  happening, records the verdict (real, noise, or known) in the superfan's ledger, and
  teaches the charter and baselines what was learned. Opened by clicking a superfan
  notification, or when the user says "triage <finding>", "what did the <component>
  superfan find", "go through the superfan inbox", or "mark that as noise".
argument-hint: "<component> [finding-id]"
---

# Triage a superfan finding

The verdict is the point. A superfan without verdicts keeps raising the same thing until
someone mutes it.

The runner is `${CLAUDE_PLUGIN_ROOT}/scripts/superfan.py` (`SF` below). The component's files
are in `${SUPERFAN_HOME:-~/.superfans}/<component>/`.

## 1. Load the finding

With a finding id, read `inbox/<finding-id>.md`. Without one, list `inbox/` (frontmatter
gives severity, title, and how many times it was seen) and go through them oldest first.
Read `charter.md` and `baselines.md` too, so you know what the superfan compared against.

## 2. Show it, then check it is still true

Lead with the title, the evidence, and the suspected cause, short. Then re-run the evidence
queries with the user's telemetry tools to see whether it is still happening, better, or
worse. Report the numbers next to the finding's numbers.

## 3. Get the verdict

Ask which it is, with your read of the evidence as a recommendation:

- **real**: something was wrong or is going wrong. Ask what they will do about it; that is
  theirs, not the superfan's.
- **noise**: not a problem. The fingerprint stays quiet for `suppress_noise_days`.
- **known**: an expected pattern. The fingerprint stays quiet for good.

Record it with the user's reason as the note:

```bash
python3 SF verdict <component> <finding-id> <real|noise|known> --note "<why>"
```

## 4. Teach the superfan

- **known**: add the pattern, with when it happens, to the charter's "Known patterns".
- **noise** because the baseline was wrong: fix that signal's range in `baselines.md`.
- **real** that the superfan nearly missed or raised late: tighten the charter (a signal, a
  better query, a neighbor) so next time is earlier.

Show each edit before making it.

## Next moves

- The next open finding in `inbox/`, if any.
- `python3 SF stats <component>` to see where the experiment stands.
