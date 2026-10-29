"""Quote orchestration: rating, delivery estimate and currency."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from freightdesk.adapters.manifest import load_manifest
from freightdesk.config import load_settings
from freightdesk.domain.errors import FreightError
from freightdesk.domain.quote import Quote
from freightdesk.domain.shipment import Address, Parcel, Shipment
from freightdesk.pricing.engine import RatingEngine
from freightdesk.pricing.tariffs import available_carriers, get_tariff
from freightdesk.services.currency import convert_quote
from freightdesk.services.transit import estimate_delivery
from freightdesk.utils.log import get_logger

log = get_logger(__name__)


@dataclass
class QuoteRequest:
    carrier: str
    dest_country: str
    dest_postcode: str
    parcels: list[Parcel]
    ship_date: date
    origin_country: str | None = None
    origin_postcode: str | None = None
    residential: bool = False
    service: str = "standard"
    currency: str | None = None
    reference: str = ""
    options: set[str] = field(default_factory=set)


@dataclass
class BatchResult:
    quotes: list[Quote]
    failures: list[tuple[str, str]]


class QuoteService:
    def __init__(self, engine: RatingEngine | None = None):
        self.engine = engine or RatingEngine()
        self.settings = load_settings()

    def default_origin(self) -> Address:
        return Address.parse(self.settings.origin_country, self.settings.origin_postcode)

    def build_shipment(self, request: QuoteRequest) -> Shipment:
        origin = (
            Address.parse(request.origin_country, request.origin_postcode)
            if request.origin_country and request.origin_postcode
            else self.default_origin()
        )
        destination = Address.parse(request.dest_country, request.dest_postcode, request.residential)
        return Shipment(
            carrier=request.carrier.upper(),
            origin=origin,
            destination=destination,
            parcels=tuple(request.parcels),
            ship_date=request.ship_date,
            service=request.service,
            reference=request.reference,
            options=frozenset(request.options),
        )

    def quote_shipment(self, shipment: Shipment, currency: str | None = None) -> Quote:
        quote = self.engine.price(shipment)
        tariff = get_tariff(shipment.carrier)
        quote.estimated_delivery = estimate_delivery(
            tariff,
            quote.zone,
            shipment.origin.country,
            shipment.destination.country,
            shipment.ship_date,
            shipment.service,
            saturday="saturday" in shipment.options,
        )
        target = (currency or self.settings.default_currency).upper()
        return convert_quote(quote, target, shipment.ship_date)

    def quote(self, request: QuoteRequest) -> Quote:
        return self.quote_shipment(self.build_shipment(request), request.currency)

    def quote_manifest(self, path: Path, ship_date: date, currency: str | None = None) -> BatchResult:
        shipments = load_manifest(path, self.default_origin(), ship_date)
        quotes, failures = [], []
        for shipment in shipments:
            try:
                quotes.append(self.quote_shipment(shipment, currency))
            except FreightError as exc:
                log.info("could not rate %s: %s", shipment.reference, exc)
                failures.append((shipment.reference, str(exc)))
        return BatchResult(quotes=quotes, failures=failures)

    def rate_shop(self, request: QuoteRequest) -> list[Quote]:
        """Quote the request with every carrier that serves the lane, cheapest first."""
        results = []
        for code in available_carriers():
            try:
                req = QuoteRequest(**{**request.__dict__, "carrier": code})
                results.append(self.quote(req))
            except FreightError as exc:
                log.info("%s cannot quote: %s", code, exc)
        return sorted(results, key=lambda q: (q.total.amount, q.carrier))
