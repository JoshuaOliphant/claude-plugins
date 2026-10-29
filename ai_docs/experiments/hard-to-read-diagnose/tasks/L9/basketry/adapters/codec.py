"""Decoding of inbound order requests and encoding of outbound summaries.

An order request is a JSON object such as::

    {
      "order_id": "W-1001",
      "customer_id": "C-1001",
      "channel": "web",
      "placed_on": "2026-03-02",
      "lines": [{"sku": "SCARF-MER", "quantity": 1, "gift": true}],
      "coupons": ["WARMUP"],
      "fulfillment": {"speed": "express", "gift_note": "Happy birthday!"}
    }

Anything the client leaves out is filled in from the channel template.
"""

from __future__ import annotations

from typing import Any

from ..domain.order import Contact, Fulfillment, Order, OrderLine
from ..domain.summary import OrderSummary
from ..utils.mapping import deep_merge
from ..utils.validation import (
    ValidationError,
    build_dataclass,
    optional_date,
    optional_email,
    require,
    require_customer_id,
    require_positive_int,
    require_sku,
    require_type,
)
from .catalog import Catalog, UnknownProduct
from .customers import CustomerStore, UnknownCustomer
from .templates import OrderTemplates, UnknownChannel

ORDER_FIELDS = frozenset(
    {"order_id", "customer_id", "channel", "currency", "placed_on", "lines", "coupons", "contact", "fulfillment"}
)
LINE_FIELDS = frozenset({"sku", "quantity", "gift"})
MAX_LINES = 50
MAX_QUANTITY = 99
SUPPORTED_CURRENCIES = ("USD",)


class OrderDecoder:
    def __init__(self, templates: OrderTemplates, catalog: Catalog, customers: CustomerStore):
        self.templates = templates
        self.catalog = catalog
        self.customers = customers

    def decode(self, payload: Any) -> Order:
        require_type(payload, dict, "order")
        unknown = sorted(set(payload) - ORDER_FIELDS)
        require(not unknown, f"order: unknown field(s) {', '.join(unknown)}", field="order")

        channel = payload.get("channel")
        try:
            template = self.templates.for_channel(channel)
        except UnknownChannel as exc:
            raise ValidationError(str(exc), field="channel") from exc
        merged = deep_merge(template, payload)

        order_id = merged.get("order_id")
        require_type(order_id, str, "order_id")
        require(bool(order_id.strip()), "order_id must not be blank", field="order_id")

        customer_id = require_customer_id(merged.get("customer_id"))
        try:
            customer = self.customers.get(customer_id)
        except UnknownCustomer as exc:
            raise ValidationError(str(exc), field="customer_id") from exc

        currency = merged.get("currency")
        require(currency in SUPPORTED_CURRENCIES, f"unsupported currency {currency!r}", field="currency")

        contact = build_dataclass(Contact, merged["contact"], context="contact")
        contact.email = optional_email(contact.email, "contact.email") or customer.email

        fulfillment = build_dataclass(Fulfillment, merged["fulfillment"], context="fulfillment")
        if fulfillment.gift_note is not None:
            require_type(fulfillment.gift_note, str, "fulfillment.gift_note")
            fulfillment.gift_note = fulfillment.gift_note.strip() or None

        coupons = merged["coupons"]
        require_type(coupons, list, "coupons")
        for index, code in enumerate(coupons):
            require_type(code, str, f"coupons[{index}]")

        return Order(
            order_id=order_id.strip(),
            customer=customer,
            channel=channel or "web",
            currency=currency,
            lines=self._decode_lines(merged.get("lines")),
            fulfillment=fulfillment,
            contact=contact,
            coupons=tuple(dict.fromkeys(code.strip().upper() for code in coupons)),
            placed_on=optional_date(merged.get("placed_on"), "placed_on"),
        )

    def _decode_lines(self, raw_lines: Any) -> list[OrderLine]:
        require_type(raw_lines, list, "lines")
        require(0 < len(raw_lines) <= MAX_LINES, f"an order needs 1 to {MAX_LINES} lines", field="lines")
        quantities: dict[tuple[str, bool], int] = {}
        for index, raw in enumerate(raw_lines):
            where = f"lines[{index}]"
            require_type(raw, dict, where)
            unknown = sorted(set(raw) - LINE_FIELDS)
            require(not unknown, f"{where}: unknown field(s) {', '.join(unknown)}", field=where)
            sku = require_sku(raw.get("sku"), f"{where}.sku")
            quantity = require_positive_int(raw.get("quantity", 1), f"{where}.quantity", maximum=MAX_QUANTITY)
            gift = raw.get("gift", False)
            require_type(gift, bool, f"{where}.gift")
            key = (sku, gift)
            quantities[key] = quantities.get(key, 0) + quantity

        lines: list[OrderLine] = []
        for (sku, gift), quantity in quantities.items():
            try:
                product = self.catalog.get(sku)
            except UnknownProduct as exc:
                raise ValidationError(str(exc), field="lines") from exc
            if gift and not product.giftable:
                raise ValidationError(f"{product.name} cannot be gift wrapped", field="lines")
            require(quantity <= MAX_QUANTITY, f"{sku}: at most {MAX_QUANTITY} per order", field="lines")
            lines.append(
                OrderLine(
                    sku=product.sku,
                    name=product.name,
                    category=product.category,
                    quantity=quantity,
                    unit_price_cents=product.price_cents,
                    weight_grams=product.weight_grams,
                    tax_class=product.tax_class,
                    gift=gift,
                )
            )
        return lines


def encode_summary(summary: OrderSummary) -> dict[str, Any]:
    """Convert a summary to the JSON shape returned by the API."""
    data = summary.to_dict()
    data["lines"] = [
        {
            "sku": line["sku"],
            "name": line["name"],
            "quantity": line["quantity"],
            "unit_price_cents": line["unit_price_cents"],
            "total_cents": line["total_cents"],
            "gift": line["gift"],
        }
        for line in data["lines"]
    ]
    data["adjustments"] = [
        {"code": a["code"], "description": a["description"], "amount_cents": a["amount_cents"]}
        for a in data["adjustments"]
    ]
    return data
