from functools import lru_cache

from .data import rows_for

FX = {"USD": 1.0, "EUR": 0.92}


def _net(rows, include_refunds):
    total = 0.0
    for r in rows:
        if r["refund"]:
            if include_refunds:
                total -= r["amount"]
        else:
            total += r["amount"]
    return total


@lru_cache(maxsize=64)
def summarize(cfg):
    rows = rows_for(cfg.region)
    net = _net(rows, cfg.include_refunds) * FX[cfg.currency]
    return {"title": cfg.title, "rows": len(rows), "net": round(net, cfg.rounding)}
