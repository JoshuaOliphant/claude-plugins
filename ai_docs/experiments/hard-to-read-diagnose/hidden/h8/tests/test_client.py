from apiclient.client import client_for
from apiclient.config import DEFAULTS


def test_tenants_do_not_leak_into_each_other():
    acme = client_for("acme")
    globex = client_for("globex")
    assert acme.request_headers()["X-Tenant"] == "acme"
    assert globex.request_headers()["X-Tenant"] == "globex"


def test_anonymous_client_has_no_tenant_header():
    client_for("acme")
    assert "X-Tenant" not in client_for().request_headers()


def test_defaults_untouched_and_overrides_still_work():
    client_for("acme", timeout=30)
    assert "X-Tenant" not in DEFAULTS["headers"]
    c = client_for(timeout=30)
    assert c.config["timeout"] == 30 and c.config["retries"] == 3
