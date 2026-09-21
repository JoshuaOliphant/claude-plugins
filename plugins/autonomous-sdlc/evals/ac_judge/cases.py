# ABOUTME: Hand-labeled evidence cases for the VERIFY AC judge, against the auth spec in spec.md.
# ABOUTME: Each case pairs one AC with passing test code and the judgment a careful reviewer would give.

CASES = [
    {
        "name": "ac1-full",
        "ac": "AC-1",
        "expected": "supports",
        "tests": [
            """def test_successful_login(client, alice):
    response = client.post("/login", data={"email": "alice@example.com", "password": alice.password})
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"
    assert Session.query.filter_by(user_id=alice.id).count() == 1"""
        ],
    },
    {
        "name": "ac1-redirect-only",
        "ac": "AC-1",
        "expected": "partial",
        "tests": [
            '''def test_successful_login(client, alice):
    response = client.post("/login", data={"email": "alice@example.com", "password": alice.password})
    assert response.headers["Location"] == "/dashboard"'''
        ],
    },
    {
        "name": "ac1-name-claims-too-much",
        "ac": "AC-1",
        "expected": "partial",
        "tests": [
            '''def test_login_redirects_and_creates_session(client, alice):
    """Covers AC-1 fully: redirect and session token."""
    response = client.post("/login", data={"email": "alice@example.com", "password": alice.password})
    assert response.status_code == 302'''
        ],
    },
    {
        "name": "ac2-full-bdd-steps",
        "ac": "AC-2",
        "expected": "supports",
        "tests": [
            """@when("the user submits the login form with an incorrect password", target_fixture="response")
def submit_wrong_password(client):
    return client.post("/login", data={"email": "alice@example.com", "password": "wrong"})""",
            """@then(parsers.parse('the system displays "{message}"'))
def displays(response, message):
    assert message in response.text""",
            '''@then("the user remains on the login page")
def remains_on_login(response):
    assert response.status_code == 200
    assert response.request.url.path == "/login"''',
            """@then("the failed attempt is logged")
def attempt_logged(caplog):
    assert any("failed login" in r.message and "alice@example.com" in r.message for r in caplog.records)""",
        ],
    },
    {
        "name": "ac2-wrong-message",
        "ac": "AC-2",
        "expected": "contradicts",
        "tests": [
            """def test_wrong_password(client, caplog):
    response = client.post("/login", data={"email": "alice@example.com", "password": "wrong"})
    assert "Incorrect password" in response.text
    assert response.request.url.path == "/login"
    assert any("failed login" in r.message for r in caplog.records)"""
        ],
    },
    {
        "name": "ac2-no-logging-check",
        "ac": "AC-2",
        "expected": "partial",
        "tests": [
            '''def test_wrong_password(client):
    response = client.post("/login", data={"email": "alice@example.com", "password": "wrong"})
    assert "Invalid credentials" in response.text
    assert response.request.url.path == "/login"'''
        ],
    },
    {
        "name": "ac3-full",
        "ac": "AC-3",
        "expected": "supports",
        "tests": [
            """def test_lockout_after_fifth_failure(client, alice, frozen_clock):
    for _ in range(4):
        client.post("/login", data={"email": "alice@example.com", "password": "wrong"})
    response = client.post("/login", data={"email": "alice@example.com", "password": "wrong"})
    assert "Account locked. Try again in 15 minutes." in response.text
    assert alice.reload().locked_until == frozen_clock.now() + timedelta(minutes=15)"""
        ],
    },
    {
        "name": "ac3-wrong-duration",
        "ac": "AC-3",
        "expected": "contradicts",
        "tests": [
            """def test_lockout_after_fifth_failure(client, alice, frozen_clock):
    for _ in range(5):
        client.post("/login", data={"email": "alice@example.com", "password": "wrong"})
    assert alice.reload().locked_until == frozen_clock.now() + timedelta(minutes=5)"""
        ],
    },
    {
        "name": "ac3-mocked-unit-under-test",
        "ac": "AC-3",
        "expected": "says_nothing",
        "tests": [
            """def test_lockout(mocker):
    lockout = mocker.patch("app.auth.lock_account", return_value=timedelta(minutes=15))
    assert lockout("alice@example.com") == timedelta(minutes=15)"""
        ],
    },
    {
        "name": "ac3-evidence-for-other-ac",
        "ac": "AC-3",
        "expected": "says_nothing",
        "tests": [
            """def test_forgot_password(client, outbox):
    response = client.post("/forgot-password", data={"email": "alice@example.com"})
    assert len(outbox) == 1
    assert "Check your email for reset instructions" in response.text"""
        ],
    },
    {
        "name": "ac4-full",
        "ac": "AC-4",
        "expected": "supports",
        "tests": [
            """def test_forgot_password(client, outbox):
    response = client.post("/forgot-password", data={"email": "alice@example.com"})
    assert len(outbox) == 1
    assert outbox[0].to == ["alice@example.com"]
    assert "Check your email for reset instructions" in response.text"""
        ],
    },
    {
        "name": "ac4-stub-step",
        "ac": "AC-4",
        "expected": "says_nothing",
        "tests": [
            """@then("a password reset email is sent")
def reset_email_sent():
    pass""",
            """@then(parsers.parse('the system displays "{message}"'))
def displays(message):
    assert message""",
        ],
    },
    {
        "name": "ac4-message-only",
        "ac": "AC-4",
        "expected": "partial",
        "tests": [
            """def test_forgot_password(client):
    response = client.post("/forgot-password", data={"email": "alice@example.com"})
    assert "Check your email for reset instructions" in response.text"""
        ],
    },
    {
        "name": "ac4-tautology",
        "ac": "AC-4",
        "expected": "says_nothing",
        "tests": [
            '''def test_password_reset_flow():
    """AC-4: reset email is sent and confirmation shown."""
    expected = "Check your email for reset instructions"
    assert expected == "Check your email for reset instructions"'''
        ],
    },
]
