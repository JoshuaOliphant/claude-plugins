# freightdesk

Parcel rating for the shipping desk. Quotes Nordline, AlpenPost and SwiftPak
shipments from our Berlin warehouse using the carriers' published rate cards.

```
python -m freightdesk quote --to DE-80331 --parcel 40x30x20@2.5
python -m freightdesk quote --carrier ALPENPOST --to AT-1010 --dims 30x20x10 --weight 1.2 --currency CHF
python -m freightdesk shop --to NL-1012AB --parcel 50x40x30@4
python -m freightdesk batch data/samples/manifest-2026-10.csv --ship-date 2026-10-05 --summary
python -m freightdesk tariff NORDLINE
python -m freightdesk cache
```

## Layout

- `freightdesk/domain` – money, shipments, parcels, quotes
- `freightdesk/pricing` – tariffs, zoning, parcel measurement, surcharges, rating engine
- `freightdesk/services` – quoting, transit estimates, currency conversion, reports
- `freightdesk/adapters` – manifest CSV, FX reference rates, output rendering
- `freightdesk/utils` – decimals, postcodes, holidays, persistent cache, logging
- `data/tariffs/*.json` – carrier rate cards (replaced when a carrier publishes a new revision)
- `data/lanes/*.csv` – zones per origin/destination country
- `data/fx/eurofxref-hist.csv` – EUR reference rates
- `etc/freightdesk.ini` – site configuration
- `var/cache` – persistent results cache shared by all desk machines

## Configuration

`etc/freightdesk.ini` sets the data and cache directories and the default
carrier, currency and origin. Environment overrides: `FREIGHTDESK_HOME`,
`FREIGHTDESK_CACHE_DIR`, `FREIGHTDESK_LOG_LEVEL`.

## Rating rules

Billable weight is the greater of actual and dimensional weight
(`L x W x H / divisor`, divisor from the rate card), rounded up to the
carrier's weight step. The parcel is priced from the first weight band that
covers its billable weight; express multiplies base freight; surcharges are
added; fuel is a percentage of everything before it.
