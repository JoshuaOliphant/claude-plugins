from decimal import Decimal

from ledger.book import balances

# Golden balances from finance's month-end reconciliation.


def test_acct_13_reconciles():
    assert balances()["acct-13"] == Decimal("-12609.13")


def test_acct_20_reconciles():
    assert balances()["acct-20"] == Decimal("-3606.00")
