from .handlers import REGISTRY

ALIASES = {"charge_back": "chargeback", "xfer": "transfer", "adj": "adjust"}


def handler_for(ev):
    kind = ALIASES.get(ev["kind"], ev["kind"])
    version = ev.get("schema", "v1").lstrip("vV")
    for v in range(int(version), 0, -1):
        h = REGISTRY.get(f"{kind}v{v}")
        if h is not None:
            return h
    raise KeyError(f"no handler for {kind} {version}")
