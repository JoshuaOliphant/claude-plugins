from .config import build_config


class Client:
    def __init__(self, **overrides):
        self.config = build_config(**overrides)

    def for_tenant(self, tenant):
        """A client acting on behalf of one tenant."""
        self.config["headers"]["X-Tenant"] = tenant
        return self

    def request_headers(self):
        return dict(self.config["headers"])


def client_for(tenant=None, **overrides):
    c = Client(**overrides)
    return c.for_tenant(tenant) if tenant else c
