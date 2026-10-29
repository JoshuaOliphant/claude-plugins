"""Output formatting for quotes."""

from __future__ import annotations

import json
from string import Template
from typing import Callable, Iterable

from freightdesk.domain.quote import Quote

_HEADER = Template("$carrier quote $reference(tariff $revision, $service, zone $zone)")
_PARCEL = Template(
    "  parcel $parcel: actual $actual_kg kg, dim $dim_weight_kg kg -> billable $billable_kg kg"
)
_LINE = Template("  $code_padded $description_padded $amount")

Renderer = Callable[[Quote], str]
_RENDERERS: dict[str, Renderer] = {}


def renderer(name: str) -> Callable[[Renderer], Renderer]:
    def register(fn: Renderer) -> Renderer:
        _RENDERERS[name] = fn
        return fn

    return register


@renderer("text")
def render_text(quote: Quote) -> str:
    out = [
        _HEADER.substitute(
            carrier=quote.carrier,
            reference=f"{quote.reference} " if quote.reference else "",
            revision=quote.tariff_revision,
            service=quote.service,
            zone=quote.zone,
        )
    ]
    for p in quote.parcels:
        data = p.to_json()
        out.append(_PARCEL.substitute(data))
    for line in quote.lines:
        out.append(
            _LINE.substitute(
                code_padded=line.code.ljust(12),
                description_padded=line.description[:44].ljust(44),
                amount=f"{line.amount.amount:>9.2f}",
            )
        )
    out.append(f"  {'TOTAL'.ljust(12)} {''.ljust(44)} {quote.total.amount:>9.2f} {quote.currency}")
    if quote.fx_rate is not None:
        out.append(f"  (converted at {quote.fx_rate} {quote.currency}/EUR)")
    if quote.estimated_delivery:
        out.append(f"  estimated delivery: {quote.estimated_delivery.isoformat()}")
    return "\n".join(out)


@renderer("json")
def render_json(quote: Quote) -> str:
    return json.dumps(quote.to_json(), indent=2, sort_keys=True)


@renderer("csv")
def render_csv(quote: Quote) -> str:
    billable = sum(float(p.billable_kg) for p in quote.parcels)
    return ",".join(
        [
            quote.reference,
            quote.carrier,
            quote.zone,
            f"{billable:g}",
            f"{quote.total.amount:.2f}",
            quote.currency,
        ]
    )


def render(quote: Quote, fmt: str = "text") -> str:
    try:
        return _RENDERERS[fmt](quote)
    except KeyError:
        raise ValueError(f"unknown format {fmt!r}; choose from {', '.join(sorted(_RENDERERS))}") from None


def render_many(quotes: Iterable[Quote], fmt: str = "text") -> str:
    quotes = list(quotes)
    if fmt == "json":
        return json.dumps([q.to_json() for q in quotes], indent=2, sort_keys=True)
    if fmt == "csv":
        header = "reference,carrier,zone,billable_kg,total,currency"
        return "\n".join([header] + [render_csv(q) for q in quotes])
    return "\n\n".join(render(q, fmt) for q in quotes)


def formats() -> list[str]:
    return sorted(_RENDERERS)
