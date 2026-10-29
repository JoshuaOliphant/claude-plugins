# ledgerkit

Import a personal ledger, check it, summarise it, export it.

    python -m ledgerkit summary data/sample.ledger
    python -m ledgerkit validate data/sample.ledger --today 2026-04-01
    python -m ledgerkit export data/sample.ledger -o report.csv
    python -m ledgerkit export data/sample.ledger -f markdown -o report.md
    python -m ledgerkit formats

Input and output formats are plug-ins: drop a module into
`ledgerkit/importers/` or `ledgerkit/exporters/` and it is picked up at
start-up. Configuration is read from `conf.d/*.ini` (later files win) and
`LEDGERKIT_<SECTION>_<KEY>` environment variables.
