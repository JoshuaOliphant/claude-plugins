# basketry

Order pricing and customer-facing order summaries for a small online shop.

    python -m basketry summarize samples/requests.jsonl        # plain-text receipts
    python -m basketry summarize --format json samples/requests.jsonl
    python -m basketry catalog --category kitchen
    python -m basketry customers --tier gold
    python -m basketry serve --port 8080                       # POST /summaries

In-process:

    from basketry import api
    api.summarize({"order_id": "W-1", "customer_id": "C-1002",
                   "lines": [{"sku": "MUG-STONE", "quantity": 2}]})

Data files live in `basketry/data/` (override the directory with
`BASKETRY_DATA_DIR`, or individual settings with a JSON file named in
`BASKETRY_SETTINGS`). Order requests may omit anything their sales channel
provides defaults for; see `order_defaults.json`.

Layout:

- `basketry/domain/` – orders, products, customers, money, summaries
- `basketry/services/` – pricing, promotions, tax, shipping, packing, summary assembly
- `basketry/adapters/` – JSON data stores, request decoding, renderers, HTTP shim, journal
- `basketry/utils/` – mapping, validation, text and registry helpers
