import glob
import json
import os
from pathlib import Path

CONF_D = Path(__file__).resolve().parent.parent / "conf.d"


def merge(base, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            merge(base[k], v)
        else:
            base[k] = v
    return base


def load(conf_d=CONF_D):
    """Merge every *.json in conf.d; files named later (10-, 20-, ...) override earlier ones."""
    cfg = {}
    for path in glob.glob(os.path.join(conf_d, "*.json")):
        merge(cfg, json.loads(Path(path).read_text()))
    return cfg
