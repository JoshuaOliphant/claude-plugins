# superfan glossary

| Term | Meaning |
|---|---|
| superfan | A scheduled headless Claude watching one component's telemetry. |
| component | The one thing a superfan watches; names its directory under `$SUPERFAN_HOME`. |
| charter | `charter.md`: what the component is, its signals (tool + query + normal), known patterns, neighbors. |
| signal | One query the superfan runs every pass. |
| baseline | Observed normal per signal by time of day and weekday, in `baselines.md`. |
| journal | `journal.md`: the superfan's own notes per pass; the last 24h go into every prompt, a week is kept. |
| long-term memory | `long_term.md`: what the superfan decided should outlive the journal; it rewrites it. |
| pass | One `superfan.py run`: one headless session and one report. |
| finding | One anomaly a pass raised, a file in `inbox/` until it has a verdict, then `closed/`. |
| fingerprint | A finding's stable signal-and-scope key; dedupe and suppression match on it. |
| page / digest | A finding's severity: notify now, or append to the day's digest. |
| verdict | The human's call on a finding: real, noise, or known. Recorded in `ledger.jsonl`. |
| blind | A pass that could not see its signals; counts as a failure. |
| neighbor | Another superfan whose recent findings this one reads. |
