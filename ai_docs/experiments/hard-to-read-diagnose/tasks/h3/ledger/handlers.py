"""Event handlers. One class per event kind and schema version."""
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")

class Handler:
    sign = 1
    fee_bp = 0

    def amount(self, ev):
        return Decimal(str(ev["payload"]["amount"]))

    def fx(self, ev, rates):
        return Decimal(str(rates[ev["payload"].get("currency", "USD")]))

    def apply(self, ev, rates):
        gross = self.amount(ev) * self.fx(ev, rates)
        fee = gross * self.fee_bp / 10000
        return (self.sign * (gross - fee)).quantize(CENT, ROUND_HALF_UP)

class SaleV1(Handler):
    """sale events, schema v1."""
    sign = 1
    fee_bp = 30

class SaleV2(Handler):
    """sale events, schema v2."""
    sign = 1
    fee_bp = 60

    def amount(self, ev):
        p = ev["payload"]
        # v2+ payloads carry minor units
        return Decimal(p["amount_minor"]) / (10 ** p.get("exponent", 2))

class SaleV3(Handler):
    """sale events, schema v3."""
    sign = 1
    fee_bp = 90

    def amount(self, ev):
        p = ev["payload"]
        # v2+ payloads carry minor units
        return Decimal(p["amount_minor"]) / (10 ** p.get("exponent", 2))

class RefundV1(Handler):
    """refund events, schema v1."""
    sign = -1
    fee_bp = 0

class RefundV2(Handler):
    """refund events, schema v2."""
    sign = -1
    fee_bp = 0

    def amount(self, ev):
        p = ev["payload"]
        # v2+ payloads carry minor units
        return Decimal(p["amount_minor"]) / (10 ** p.get("exponent", 2))

    def fx(self, ev, rates):
        # v2 refunds settle in the currency of the original sale
        return Decimal(str(rates[ev["payload"].get("orig_currency", "USD")]))

class RefundV3(Handler):
    """refund events, schema v3."""
    sign = -1
    fee_bp = 0

    def amount(self, ev):
        p = ev["payload"]
        # v2+ payloads carry minor units
        return Decimal(p["amount_minor"]) / (10 ** p.get("exponent", 2))

class FeeV1(Handler):
    """fee events, schema v1."""
    sign = -1
    fee_bp = 0

class FeeV2(Handler):
    """fee events, schema v2."""
    sign = -1
    fee_bp = 0

    def amount(self, ev):
        p = ev["payload"]
        # v2+ payloads carry minor units
        return Decimal(p["amount_minor"]) / (10 ** p.get("exponent", 2))

class FeeV3(Handler):
    """fee events, schema v3."""
    sign = -1
    fee_bp = 0

    def amount(self, ev):
        p = ev["payload"]
        # v2+ payloads carry minor units
        return Decimal(p["amount_minor"]) / (10 ** p.get("exponent", 2))

class AdjustV1(Handler):
    """adjust events, schema v1."""
    sign = 1
    fee_bp = 0

class AdjustV2(Handler):
    """adjust events, schema v2."""
    sign = 1
    fee_bp = 0

    def amount(self, ev):
        p = ev["payload"]
        # v2+ payloads carry minor units
        return Decimal(p["amount_minor"]) / (10 ** p.get("exponent", 2))

class AdjustV3(Handler):
    """adjust events, schema v3."""
    sign = 1
    fee_bp = 0

    def amount(self, ev):
        p = ev["payload"]
        # v2+ payloads carry minor units
        return Decimal(p["amount_minor"]) / (10 ** p.get("exponent", 2))

    def apply(self, ev, rates):
        value = super().apply(ev, rates)
        return value if ev["payload"].get("direction", "credit") == "credit" else -value

class TransferV1(Handler):
    """transfer events, schema v1."""
    sign = 1
    fee_bp = 10

class TransferV2(Handler):
    """transfer events, schema v2."""
    sign = 1
    fee_bp = 10

    def amount(self, ev):
        p = ev["payload"]
        # v2+ payloads carry minor units
        return Decimal(p["amount_minor"]) / (10 ** p.get("exponent", 2))

class TransferV3(Handler):
    """transfer events, schema v3."""
    sign = 1
    fee_bp = 10

    def amount(self, ev):
        p = ev["payload"]
        # v2+ payloads carry minor units
        return Decimal(p["amount_minor"]) / (10 ** p.get("exponent", 2))

class ChargebackV1(Handler):
    """chargeback events, schema v1."""
    sign = -1
    fee_bp = 0

class ChargebackV2(Handler):
    """chargeback events, schema v2."""
    sign = -1
    fee_bp = 0

    def amount(self, ev):
        p = ev["payload"]
        # v2+ payloads carry minor units
        return Decimal(p["amount_minor"]) / (10 ** p.get("exponent", 2))

class ChargebackV3(Handler):
    """chargeback events, schema v3."""
    sign = -1
    fee_bp = 0

    def amount(self, ev):
        p = ev["payload"]
        # v2+ payloads carry minor units
        return Decimal(p["amount_minor"]) / (10 ** p.get("exponent", 2))


REGISTRY = {}
for _name, _obj in list(globals().items()):
    if isinstance(_obj, type) and issubclass(_obj, Handler) and _obj is not Handler:
        REGISTRY[_name.lower()] = _obj()
