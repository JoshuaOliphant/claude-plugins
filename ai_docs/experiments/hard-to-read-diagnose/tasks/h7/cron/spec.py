import re

UNITS = {"m": 60, "h": 3600, "d": 86400}


def parse_every(text):
    """'30m', '6h', '1d' -> seconds between runs."""
    m = re.fullmatch(r"(\d+)([mhd])", text.strip())
    if not m:
        raise ValueError(f"bad interval {text!r}")
    return int(m.group(1)) * UNITS[m.group(2)]
