# ABOUTME: Hand-labeled cases for the non-comment jev-lint rules: each is a source or diff snippet and whether the rule should flag it.
# ABOUTME: Comment-kind cases come from git history instead (see comments.jsonl), since cleanup commits already labeled them.


def diff(path: str, removed: list[str], added: list[str], context: list[str] = ()) -> str:
    body = [f" {line}" for line in context]
    body += [f"-{line}" for line in removed] + [f"+{line}" for line in added]
    return "\n".join(
        [
            f"diff --git a/{path} b/{path}",
            f"--- a/{path}",
            f"+++ b/{path}",
            f"@@ -10,{len(context) + len(removed)} +10,{len(context) + len(added)} @@",
            *body,
        ]
    )


CASES = [
    # silent-failure
    {
        "rule": "silent-failure",
        "flag": True,
        "source": """
def load_settings(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        pass
""",
    },
    {
        "rule": "silent-failure",
        "flag": True,
        "source": """
def fetch_prices(client, skus):
    prices = {}
    for sku in skus:
        try:
            prices[sku] = client.price(sku)
        except Exception as error:
            logger.debug("price lookup failed for %s: %s", sku, error)
            continue
    return prices
""",
    },
    {
        "rule": "silent-failure",
        "flag": True,
        "source": """
def parse_config(text):
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return {}
""",
    },
    {
        "rule": "silent-failure",
        "flag": False,
        "source": """
def read_optional_overrides(path):
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return ""
""",
    },
    {
        "rule": "silent-failure",
        "flag": False,
        "source": """
def lookup(config, key):
    try:
        return config[key]
    except KeyError as error:
        raise ConfigError(f"missing required setting {key!r}") from error
""",
    },
    {
        "rule": "silent-failure",
        "flag": False,
        "source": """
def run_job(job):
    try:
        job.execute()
    except Exception:
        logger.exception("job %s failed", job.id)
        raise
""",
    },
    # io-mixed-with-logic
    {
        "rule": "io-mixed-with-logic",
        "flag": True,
        "source": """
def apply_discounts(orders_path, out_path):
    orders = json.loads(Path(orders_path).read_text())
    for order in orders:
        if order["total"] > 100 and order["customer_tier"] == "gold":
            order["total"] *= 0.85
        elif order["items"] >= 5:
            order["total"] -= 10
    Path(out_path).write_text(json.dumps(orders))
""",
    },
    {
        "rule": "io-mixed-with-logic",
        "flag": True,
        "source": """
def refund_eligible(order_id):
    order = httpx.get(f"{API}/orders/{order_id}").json()
    days = (date.today() - date.fromisoformat(order["delivered"])).days
    return order["status"] == "delivered" and days <= 30 and not order["final_sale"]
""",
    },
    {
        "rule": "io-mixed-with-logic",
        "flag": False,
        "source": """
def discounted_total(total, tier, item_count):
    if total > 100 and tier == "gold":
        return total * 0.85
    if item_count >= 5:
        return total - 10
    return total
""",
    },
    {
        "rule": "io-mixed-with-logic",
        "flag": False,
        "source": """
def main(argv):
    args = parse_args(argv)
    orders = load_orders(args.input)
    priced = [price_order(order) for order in orders]
    save_orders(args.output, priced)
""",
    },
    {
        "rule": "io-mixed-with-logic",
        "flag": False,
        "source": """
def save_orders(path, orders):
    Path(path).write_text(json.dumps([asdict(order) for order in orders], indent=2))
""",
    },
    # name-hides-side-effects
    {
        "rule": "name-hides-side-effects",
        "flag": True,
        "source": """
def get_user(db, user_id):
    user = db.fetch(user_id)
    user.last_seen = datetime.now()
    db.save(user)
    return user
""",
    },
    {
        "rule": "name-hides-side-effects",
        "flag": True,
        "source": """
def format_report(rows):
    rows.sort(key=lambda row: row.total, reverse=True)
    return "\\n".join(f"{row.name}: {row.total}" for row in rows)
""",
    },
    {
        "rule": "name-hides-side-effects",
        "flag": True,
        "source": """
def validate_config(config):
    if "api_url" not in config:
        print("missing api_url")
        sys.exit(1)
    return config
""",
    },
    {
        "rule": "name-hides-side-effects",
        "flag": False,
        "source": """
def save_report(rows, path):
    Path(path).write_text("\\n".join(f"{row.name}: {row.total}" for row in rows))
""",
    },
    {
        "rule": "name-hides-side-effects",
        "flag": False,
        "source": """
def order_total(items):
    return sum(item.price * item.quantity for item in items)
""",
    },
    {
        "rule": "name-hides-side-effects",
        "flag": False,
        "source": """
def cmd_tick(args):
    state = load()
    state["iteration"] += 1
    save(state)
    print(f"iteration {state['iteration']}")
""",
    },
    # docstring-quality
    {
        "rule": "docstring-quality",
        "flag": True,
        "source": '''
def parse_date(text):
    """Parse a date."""
    return datetime.strptime(text, "%Y-%m-%d").date()
''',
    },
    {
        "rule": "docstring-quality",
        "flag": True,
        "source": '''
def find_user(users, email):
    """Return the user with this email, or None when there is no match."""
    return users[email]
''',
    },
    {
        "rule": "docstring-quality",
        "flag": True,
        "source": '''
def read_settings(path):
    """Return the settings stored at path."""
    if not path.exists():
        path.write_text(json.dumps(DEFAULTS))
    return json.loads(path.read_text())
''',
    },
    {
        "rule": "docstring-quality",
        "flag": False,
        "source": '''
def parse_timestamp(text):
    """Parse an ISO-8601 timestamp; naive values are treated as UTC.

    Raises ValueError for timestamps before 1970."""
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    if value.year < 1970:
        raise ValueError(f"timestamp before epoch: {text}")
    return value
''',
    },
    {
        "rule": "docstring-quality",
        "flag": False,
        "source": '''
def backoff_delay(attempt, base=0.5, cap=30.0):
    """Exponential backoff capped at `cap` seconds, so retry storms stay bounded."""
    return min(cap, base * 2**attempt)
''',
    },
    # log-exposure
    {
        "rule": "log-exposure",
        "flag": True,
        "source": """
def login(email, password):
    logger.info("login attempt for %s with password %s", email, password)
    return auth.check(email, password)
""",
    },
    {
        "rule": "log-exposure",
        "flag": True,
        "source": """
def connect(settings):
    api_token = settings["token"]
    logger.debug("connecting with token=%s", api_token)
    return Client(api_token)
""",
    },
    {
        "rule": "log-exposure",
        "flag": True,
        "source": """
def charge(customer, card_number, amount):
    logger.info("charging card %s for %s", card_number, amount)
    return gateway.charge(card_number, amount)
""",
    },
    {
        "rule": "log-exposure",
        "flag": False,
        "source": """
def process(rows, started):
    elapsed = time.perf_counter() - started
    logger.info("processed %d rows in %.2fs", len(rows), elapsed)
""",
    },
    {
        "rule": "log-exposure",
        "flag": False,
        "source": """
def fetch(url, attempt):
    logger.warning("retrying request to %s (attempt %d)", url, attempt)
    return httpx.get(url)
""",
    },
    # test-smell
    {
        "rule": "test-smell",
        "flag": True,
        "source": """
def test_discount_applied():
    expected = 85.0
    assert expected == 85.0
""",
    },
    {
        "rule": "test-smell",
        "flag": True,
        "source": """
def test_refund_eligible(mocker):
    eligible = mocker.patch("shop.refunds.is_refundable", return_value=True)
    assert eligible(order_id=7) is True
""",
    },
    {
        "rule": "test-smell",
        "flag": True,
        "source": """
def test_checkout_charges_card_and_sends_receipt(client, outbox):
    response = client.post("/checkout", json={"cart": 1})
    assert response.status_code == 200
""",
    },
    {
        "rule": "test-smell",
        "flag": True,
        "source": """
def test_parse_report():
    result = parse_report(SAMPLE)
    assert result is not None
""",
    },
    {
        "rule": "test-smell",
        "flag": False,
        "source": """
def test_gold_customers_get_fifteen_percent_off():
    assert discounted_total(200, "gold", 1) == 170
""",
    },
    {
        "rule": "test-smell",
        "flag": False,
        "source": """
def test_missing_setting_raises_config_error():
    with pytest.raises(ConfigError, match="api_url"):
        lookup({}, "api_url")
""",
    },
    # symptom-workaround
    {
        "rule": "symptom-workaround",
        "flag": True,
        "diff": diff(
            "app/sync.py",
            ["    result = client.push(batch)"],
            ["    time.sleep(2)", "    result = client.push(batch)"],
        ),
    },
    {
        "rule": "symptom-workaround",
        "flag": True,
        "diff": diff(
            "app/report.py",
            ["    return build_rows(records)"],
            [
                "    try:",
                "        return build_rows(records)",
                "    except Exception:",
                "        return []",
            ],
        ),
    },
    {
        "rule": "symptom-workaround",
        "flag": True,
        "diff": diff(
            "tests/test_sync.py",
            ["def test_push_batch(client):"],
            ['@pytest.mark.skip(reason="flaky on CI")', "def test_push_batch(client):"],
        ),
    },
    {
        "rule": "symptom-workaround",
        "flag": False,
        "diff": diff(
            "app/pages.py",
            ["    return range(1, page_count)"],
            ["    return range(1, page_count + 1)"],
            context=["def page_numbers(page_count):"],
        ),
    },
    {
        "rule": "symptom-workaround",
        "flag": False,
        "diff": diff(
            "app/orders.py",
            ["def total(o):", "    return sum(i.price for i in o.items)"],
            ["def order_total(order):", "    return sum(item.price for item in order.items)"],
        ),
    },
    {
        "rule": "symptom-workaround",
        "flag": False,
        "diff": diff(
            "app/orders.py",
            [],
            [
                "    if quantity <= 0:",
                '        raise ValueError(f"quantity must be positive: {quantity}")',
            ],
            context=["def add_item(order, sku, quantity):"],
        ),
    },
    # test-weakening
    {
        "rule": "test-weakening",
        "flag": True,
        "diff": diff(
            "tests/test_pricing.py",
            ["    assert discounted_total(200, 'gold', 1) == 170"],
            ["    assert discounted_total(200, 'gold', 1)"],
        ),
    },
    {
        "rule": "test-weakening",
        "flag": True,
        "diff": diff(
            "tests/test_pricing.py",
            ["    assert order.total == 42", "    assert order.currency == 'USD'"],
            ["    assert order.total > 0"],
        ),
    },
    {
        "rule": "test-weakening",
        "flag": True,
        "diff": diff(
            "tests/test_auth.py",
            [
                "def test_lockout_after_five_failures(client):",
                "    for _ in range(5):",
                "        fail_login(client)",
                "    assert account_locked(client)",
            ],
            [],
        ),
    },
    {
        "rule": "test-weakening",
        "flag": False,
        "diff": diff(
            "tests/test_pricing.py",
            [],
            ["    assert order.currency == 'USD'"],
            context=["    assert order.total == 42"],
        ),
    },
    {
        "rule": "test-weakening",
        "flag": False,
        "diff": diff(
            "tests/test_pricing.py",
            ["def test_1():"],
            ["def test_gold_customers_get_fifteen_percent_off():"],
            context=["    assert discounted_total(200, 'gold', 1) == 170"],
        ),
    },
    {
        "rule": "test-weakening",
        "flag": False,
        "diff": diff(
            "tests/test_pricing.py",
            ["    order = Order(items=[Item(price=42)])"],
            ["    order = make_order(prices=[42])"],
            context=["    assert order.total == 42"],
        ),
    },
    # comment-kind: text that belongs in documentation versus a why the code cannot show
    {
        "rule": "comment-kind",
        "flag": True,
        "source": """
# How to use this module: call `connect(url)` once at startup, then pass the
# returned Session to every repository class. Sessions are not thread-safe, so
# web workers should create one per request.
def connect(url):
    return Session(url)
""",
    },
    {
        "rule": "comment-kind",
        "flag": True,
        "source": """
# The pipeline has three stages. The collector polls each source every minute and
# writes raw events to the queue; the enricher joins them with account data; the
# publisher batches enriched events to the warehouse. Stages share only the queue.
QUEUE_NAME = "events"
""",
    },
    {
        "rule": "comment-kind",
        "flag": False,
        "source": """
def send(frame):
    # The device firmware drops frames larger than 512 bytes without an error.
    for chunk in split(frame, 512):
        port.write(chunk)
""",
    },
    {
        "rule": "comment-kind",
        "flag": False,
        "source": """
def parse(text):
    # Keep strict=False: vendor exports contain control characters in notes fields.
    return json.loads(text, strict=False)
""",
    },
]
