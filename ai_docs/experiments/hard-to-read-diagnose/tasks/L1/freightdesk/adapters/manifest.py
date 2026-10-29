"""Shipping manifest (CSV) reader.

Expected columns::

    reference,carrier,dest_country,dest_postcode,dims,weight_kg[,residential][,service][,options]

``dims`` uses the ``LxWxH`` form in centimetres.  Several parcels belonging to
the same reference are grouped into one shipment, in file order.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from freightdesk.domain.errors import ValidationError
from freightdesk.domain.shipment import Address, Parcel, Shipment

REQUIRED = ("reference", "carrier", "dest_country", "dest_postcode", "dims", "weight_kg")
TRUTHY = {"1", "y", "yes", "true", "x"}


@dataclass
class ManifestRow:
    line: int
    reference: str
    carrier: str
    dest_country: str
    dest_postcode: str
    dims: str
    weight_kg: str
    residential: bool
    service: str
    options: frozenset[str]


def read_rows(path: Path) -> list[ManifestRow]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValidationError(f"{path.name}: missing columns {', '.join(missing)}")
        rows = []
        for line, raw in enumerate(reader, start=2):
            if not any((v or "").strip() for v in raw.values()):
                continue
            options = frozenset(
                o.strip().lower() for o in (raw.get("options") or "").split(";") if o.strip()
            )
            rows.append(
                ManifestRow(
                    line=line,
                    reference=raw["reference"].strip(),
                    carrier=raw["carrier"].strip().upper(),
                    dest_country=raw["dest_country"].strip().upper(),
                    dest_postcode=raw["dest_postcode"].strip(),
                    dims=raw["dims"].strip(),
                    weight_kg=raw["weight_kg"].strip(),
                    residential=(raw.get("residential") or "").strip().lower() in TRUTHY,
                    service=(raw.get("service") or "standard").strip().lower() or "standard",
                    options=options,
                )
            )
        return rows


def to_shipments(rows: list[ManifestRow], origin: Address, ship_date: date) -> list[Shipment]:
    grouped: dict[str, list[ManifestRow]] = {}
    for row in rows:
        grouped.setdefault(row.reference, []).append(row)

    shipments = []
    for reference, group in grouped.items():
        head = group[0]
        for other in group[1:]:
            if (other.carrier, other.dest_country, other.dest_postcode) != (
                head.carrier,
                head.dest_country,
                head.dest_postcode,
            ):
                raise ValidationError(
                    f"line {other.line}: reference {reference} has conflicting destination/carrier"
                )
        try:
            destination = Address.parse(head.dest_country, head.dest_postcode, head.residential)
            parcels = tuple(Parcel.from_strings(r.dims, r.weight_kg) for r in group)
        except ValidationError as exc:
            raise ValidationError(f"line {head.line}: {exc}") from exc
        shipments.append(
            Shipment(
                carrier=head.carrier,
                origin=origin,
                destination=destination,
                parcels=parcels,
                ship_date=ship_date,
                service=head.service,
                reference=reference,
                options=head.options,
            )
        )
    return shipments


def load_manifest(path: Path, origin: Address, ship_date: date) -> list[Shipment]:
    return to_shipments(read_rows(path), origin, ship_date)
