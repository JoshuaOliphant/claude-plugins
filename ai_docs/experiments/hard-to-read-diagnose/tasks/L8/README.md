# stockline

Nightly supplier feed import for the product catalog.

```
python -m stockline --db catalog.json import samples/acme_2026-10-27.csv
python -m stockline --db catalog.json show AC-1003
python -m stockline --db catalog.json history AC-1003
python -m stockline --db catalog.json runs
python -m stockline --db catalog.json export catalog.csv
```

The supplier is taken from the feed file name prefix (`acme_`, `northwind_`,
`globex_`) unless `--supplier` is given.  Column layouts, category maps and
pricing rules live in `stockline/data/`.  Settings come from
`stockline/data/defaults.ini`, an optional `--config` file and `STOCKLINE_*`
environment variables.

The production job runs `import --full-feed --quiet` for each supplier drop
under cron at 02:00.
