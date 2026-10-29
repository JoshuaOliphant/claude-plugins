DEFAULTS = {
    "base_url": "https://api.example.test",
    "timeout": 10,
    "retries": 3,
    "headers": {"Accept": "application/json", "User-Agent": "apiclient/2"},
}


def build_config(**overrides):
    cfg = dict(DEFAULTS)
    cfg.update(overrides)
    return cfg
