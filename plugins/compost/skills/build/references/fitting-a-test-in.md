# Fitting a test in

A worked example of step 4 in `compost:build`: one acceptance criterion placed into an existing
pytest suite. The first attempt adds a file beside the suite. The second changes one expectation,
adds rows to a table, and extends a factory.

## The issue

> **#42 Tokens expire at their expiry instant**
>
> As an API client, I want an expired token refused at once, so that a leaked token stops
> working when it says it does.
>
> **AC-2** Given a token whose `expires_at` is now or earlier,
> When it is authorized,
> Then the decision is `Denied("expired")`.

Today `authorize` allows a 60-second grace period after expiry.

## What the suite already has

`tests/conftest.py`:

```python
@pytest.fixture
def now():
    return datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def make_token(now):
    def make(subject="ada", scopes=("read",), expires_in=timedelta(hours=1)):
        return Token(subject=subject, scopes=frozenset(scopes), expires_at=now + expires_in)

    return make
```

`tests/test_auth.py`:

```python
def test_authorize_allows(make_token, now):
    assert authorize(make_token(), required_scope="read", now=now) == Allowed("ada")


@pytest.mark.parametrize(
    ("token_fields", "reason"),
    [
        pytest.param({"subject": ""}, "anonymous", id="blank-subject"),
        pytest.param({"scopes": ()}, "missing-scope", id="no-scopes"),
        pytest.param({"expires_in": timedelta(minutes=-2)}, "expired", id="expired-past-grace"),
    ],
)
def test_authorize_denies(make_token, now, token_fields, reason):
    decision = authorize(make_token(**token_fields), required_scope="read", now=now)
    assert decision == Denied(reason)


def test_grace_period_allows_recently_expired(make_token, now):
    token = make_token(expires_in=timedelta(seconds=-30))
    assert authorize(token, required_scope="read", now=now) == Allowed("ada")
```

The survey in step 3 turns up three things to build on: the `now` fixture already injects the
clock, `make_token` already builds tokens with any expiry, and `test_authorize_denies` is the
table where every denial lives.

## Before: a test added beside the suite

`tests/test_token_expiry.py`:

```python
from unittest.mock import patch


@pytest.fixture
def expired_token():
    return Token(
        subject="ada",
        scopes=frozenset({"read"}),
        expires_at=datetime(2026, 3, 1, 11, 59, 30, tzinfo=UTC),
    )


def test_expired_token_is_denied(expired_token):
    with patch("app.auth.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
        decision = authorize(expired_token, required_scope="read", now=mock_datetime.now())
    assert decision.reason == "expired"
    assert mock_datetime.now.called


def test_long_expired_token_is_denied():
    token = Token(
        subject="ada",
        scopes=frozenset({"read"}),
        expires_at=datetime(2026, 3, 1, 11, 0, tzinfo=UTC),
    )
    decision = authorize(token, required_scope="read", now=datetime(2026, 3, 1, 12, 0, tzinfo=UTC))
    assert decision.reason == "expired"
```

It passes once the code changes, and it is still wrong in five ways:

- `expired_token` duplicates `make_token`. When `Token` gains a required field, two places break.
- It patches a module path to fake time when `now` is already injected. The patch does nothing,
  and `assert mock_datetime.now.called` only proves the test called its own mock.
- `test_long_expired_token_is_denied` re-covers `expired-past-grace`.
- `test_grace_period_allows_recently_expired` still asserts the old behavior. The suite now holds
  two tests that disagree, and one of them fails.
- The boundary the AC names, expiry at exactly `now`, is not tested at all.

## After: the criterion fitted in

The grace-period test already covers the behavior that changes, so its expectation changes
(rule 1). Its new expectation is a denial, which is what the table holds, so it becomes a row and
the standalone function is deleted. The exact-instant boundary is one more row (rule 2). No
fixture is added, because `make_token` already takes `expires_in`.

```python
@pytest.mark.parametrize(
    ("token_fields", "reason"),
    [
        pytest.param({"subject": ""}, "anonymous", id="blank-subject"),
        pytest.param({"scopes": ()}, "missing-scope", id="no-scopes"),
        pytest.param({"expires_in": timedelta(minutes=-2)}, "expired", id="expired-minutes-ago"),
        pytest.param({"expires_in": timedelta(seconds=-30)}, "expired", id="expired-seconds-ago"),
        pytest.param({"expires_in": timedelta(0)}, "expired", id="expired-at-exact-instant"),
    ],
)
def test_authorize_denies(make_token, now, token_fields, reason):
    decision = authorize(make_token(**token_fields), required_scope="read", now=now)
    assert decision == Denied(reason)
```

The row `expired-past-grace` is renamed `expired-minutes-ago`, since grace is no longer a word in
the domain. The file has one test function fewer and two rows more.

`test_authorize_allows` already covers an unexpired token, so AC-2 needs no allowed-side test.
Had that test not existed, rule 3 applies: one test in this file on `make_token` and `now`.

## Name the break, derive the value

- `expired-at-exact-instant` fails if the comparison is `now > expires_at` instead of
  `now >= expires_at`. The expected `Denied("expired")` comes from the AC's wording, "now or
  earlier", not from reading the implementation.
- `expired-seconds-ago` fails if any grace period survives.

## See it fail for the right reason

Run against the unchanged code:

```text
$ uv run pytest tests/test_auth.py -k expired -q
FAILED tests/test_auth.py::test_authorize_denies[expired-seconds-ago] - AssertionError: assert Allowed(subject='ada') == Denied(reason='expired')
FAILED tests/test_auth.py::test_authorize_denies[expired-at-exact-instant] - AssertionError: assert Allowed(subject='ada') == Denied(reason='expired')
2 failed, 1 passed, 3 deselected in 0.01s
```

Both fail on the assertion, with the old behavior on the left. That is the right reason. A
failure such as `TypeError: make() got an unexpected keyword argument 'expires_at'` would be the
wrong one: the test would be broken, not the code.

If the code was written first, undo it in the working tree for the red run and put it back:

```bash
git diff -- src/app/auth.py > /tmp/auth-42.patch
git checkout -- src/app/auth.py
uv run pytest tests/test_auth.py -k expired -q     # expect the two failures above
git apply /tmp/auth-42.patch
```

## The production change

Replace, don't deprecate. The constant goes with the behavior it supported:

```python
# before
GRACE = timedelta(seconds=60)

def authorize(token, required_scope, now):
    if not token.subject:
        return Denied("anonymous")
    if now > token.expires_at + GRACE:
        return Denied("expired")
    ...

# after
def authorize(token, required_scope, now):
    if not token.subject:
        return Denied("anonymous")
    if now >= token.expires_at:
        return Denied("expired")
    ...
```

## Mutation check

| Mutation | Tests that fail |
|---|---|
| `>=` becomes `>` | `expired-at-exact-instant` |
| a 60-second grace period comes back | `expired-seconds-ago`, `expired-at-exact-instant` |
| the expiry check is deleted | all three `expired-*` rows |
| returns `Denied("anonymous")` for expiry | all three `expired-*` rows |
| `>=` becomes `<=` | `test_authorize_allows`, `no-scopes`, two `expired-*` rows |

Every realistic mutation is caught. If you run these mutations rather than imagine them, set
`PYTHONDONTWRITEBYTECODE=1` or delete `__pycache__` between runs: an edit that keeps the file's
size and lands in the same second as the last one can leave Python running the stale bytecode,
and the run reports on code that is no longer on disk. The AC maps to
`test_authorize_denies[expired-at-exact-instant]` and
`test_authorize_denies[expired-seconds-ago]`.

## When nothing fits

Rule 4 applies only when the survey finds nothing to extend. Suppose AC-3 needs tokens signed by
a rotated key, and no fixture builds keys. Add a `signing_key` fixture to the `conftest.py` that
holds `make_token`, and let `make_token` take it as a parameter. Do not add a second token
factory in the test file that needs it.
