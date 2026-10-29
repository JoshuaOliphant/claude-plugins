import os
import subprocess
import sys

import pytest

from conftest import ACME, ACME_IDS, BANK, CARD, NOVA, NOVA_IDS, TREE, ledger_ids, write_config

from ledgerflow.app import run_import
from ledgerflow.feeds.transport import DirectoryTransport, TransientFeedError


class FlakyTransport(DirectoryTransport):
    """Fails the given page fetches (1-based, counted per feed) once each."""

    def __init__(self, root, fail_on, feed="acme"):
        super().__init__(root)
        self.fail_on = set(fail_on)
        self.feed = feed
        self.calls = 0
        self.failures = 0

    def fetch_page(self, feed, token, since=None):
        if feed == self.feed:
            self.calls += 1
            if self.calls in self.fail_on:
                self.fail_on.discard(self.calls)
                self.failures += 1
                raise TransientFeedError(f"gateway timeout on request {self.calls}")
        return super().fetch_page(feed, token, since=since)


def test_feed_clean_run_is_complete(tmp_path, no_sleep):
    result = run_import(write_config(tmp_path, [ACME]), sleep=no_sleep)
    assert result.by_name("acme-feed").imported == 120
    assert ledger_ids(tmp_path) == ACME_IDS


def test_feed_with_validation_is_complete(tmp_path, no_sleep):
    result = run_import(write_config(tmp_path, [ACME], validate=True), sleep=no_sleep)
    assert result.by_name("acme-feed").imported == 120
    assert ledger_ids(tmp_path) == ACME_IDS


def test_validate_flag_overrides_config(tmp_path, no_sleep):
    result = run_import(write_config(tmp_path, [ACME]), validate=True, sleep=no_sleep)
    assert ledger_ids(tmp_path) == ACME_IDS
    assert result.imported == 120


@pytest.mark.parametrize("fail_on", [[2], [4], [7]])
def test_feed_transient_failure_then_success_is_complete(tmp_path, no_sleep, fail_on):
    transport = FlakyTransport(TREE / "feeds", fail_on)
    result = run_import(write_config(tmp_path, [ACME]), transport=transport, sleep=no_sleep)
    assert transport.failures == 1
    assert result.by_name("acme-feed").attempts == 2
    assert ledger_ids(tmp_path) == ACME_IDS


def test_feed_failure_on_first_request_is_complete(tmp_path, no_sleep):
    transport = FlakyTransport(TREE / "feeds", [1])
    run_import(write_config(tmp_path, [ACME]), transport=transport, sleep=no_sleep)
    assert ledger_ids(tmp_path) == ACME_IDS


def test_feed_failure_with_validation_is_complete(tmp_path, no_sleep):
    transport = FlakyTransport(TREE / "feeds", [5])
    result = run_import(write_config(tmp_path, [ACME], validate=True), transport=transport,
                        sleep=no_sleep)
    assert ledger_ids(tmp_path) == ACME_IDS
    assert result.by_name("acme-feed").rejected == 0


def test_two_failures_within_retry_budget(tmp_path, no_sleep):
    transport = FlakyTransport(TREE / "feeds", [3, 6])
    run_import(write_config(tmp_path, [ACME], attempts=3), transport=transport, sleep=no_sleep)
    assert ledger_ids(tmp_path) == ACME_IDS


def test_persistent_failure_gives_up_without_partial_ledger(tmp_path, no_sleep):
    class Down(DirectoryTransport):
        def fetch_page(self, feed, token, since=None):
            if token is not None:
                raise TransientFeedError("gateway down")
            return super().fetch_page(feed, token, since=since)

    with pytest.raises(Exception):
        run_import(write_config(tmp_path, [ACME], attempts=2), transport=Down(TREE / "feeds"),
                   sleep=no_sleep)
    assert not (tmp_path / "ledger.jsonl").exists()


@pytest.mark.parametrize("validate", [False, True])
def test_consolidated_run_is_complete(tmp_path, no_sleep, validate):
    result = run_import(write_config(tmp_path, [BANK, CARD, ACME, NOVA], validate=validate),
                        sleep=no_sleep)
    assert ledger_ids(tmp_path, "acme-feed") == ACME_IDS
    assert ledger_ids(tmp_path, "nova-feed") == NOVA_IDS
    assert result.by_name("card").imported == 15
    assert result.by_name("bank").imported == (39 if validate else 40)
    assert result.by_name("bank").rejected == (1 if validate else 0)


def test_file_sources_with_validation(tmp_path, no_sleep):
    result = run_import(write_config(tmp_path, [BANK, CARD], validate=True), sleep=no_sleep)
    assert result.imported == 54
    assert len(ledger_ids(tmp_path, "bank")) == 39


def test_cli_import_with_validate(tmp_path):
    cfg = write_config(tmp_path, [ACME])
    env = dict(os.environ, PYTHONPATH=str(TREE))
    proc = subprocess.run([sys.executable, "-m", "ledgerflow", "import", str(cfg), "--validate"],
                          cwd=TREE, env=env, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert "acme-feed: 120 imported" in proc.stdout
    assert ledger_ids(tmp_path) == ACME_IDS
