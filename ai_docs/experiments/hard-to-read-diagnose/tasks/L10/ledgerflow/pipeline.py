"""The import pipeline: read, (validate), normalise, stage, commit."""

from __future__ import annotations

import functools
import logging
import time
from typing import Callable, Iterable

from ledgerflow.feeds.transport import TransientFeedError
from ledgerflow.models import ImportResult, SourceResult
from ledgerflow.normalize import NormalizationError, Normalizer
from ledgerflow.sources.base import Source
from ledgerflow.staging import StagingArea
from ledgerflow.storage import LedgerStore
from ledgerflow.utils.retry import AttemptLog, RetryPolicy, retry_call
from ledgerflow.validation import Validator

log = logging.getLogger(__name__)

RETRYABLE = (TransientFeedError, ConnectionError, TimeoutError)


class ImportPipeline:
    def __init__(
        self,
        *,
        normalizer: Normalizer,
        store: LedgerStore,
        policy: RetryPolicy,
        validator: Validator | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.normalizer = normalizer
        self.store = store
        self.policy = policy
        self.validator = validator
        self.sleep = sleep

    def run(self, sources: Iterable[Source]) -> ImportResult:
        result = ImportResult(output=str(self.store.path), base_currency=self.normalizer.base_currency)
        for source in sources:
            result.sources.append(self.import_source(source))
        self.store.close()
        return result

    def import_source(self, source: Source) -> SourceResult:
        if self.validator is not None:
            self.validator.preflight(source)

        attempts = AttemptLog()
        staging = retry_call(
            functools.partial(self._stage, source),
            self.policy,
            sleep=self.sleep,
            on_retry=functools.partial(self._on_retry, source),
            attempt_log=attempts,
        )
        committed = self.store.commit(staging.transactions)
        for rejection in staging.rejections:
            log.info("rejected %s", rejection.describe())
        return SourceResult(
            name=source.name,
            imported=committed,
            rejected=len(staging.rejections),
            duplicates=staging.duplicates,
            attempts=attempts.attempts,
            rejections=staging.rejections,
        )

    def _stage(self, source: Source) -> StagingArea:
        staging = StagingArea(source.name)
        for record in source.records():
            if self.validator is not None:
                problems = self.validator.check(record)
                if problems:
                    staging.reject(record.record_id, problems)
                    continue
            try:
                txn = self.normalizer.normalize(record, source.name)
            except NormalizationError as exc:
                staging.reject(exc.record_id, exc.reasons)
                continue
            staging.add(txn, self.store.ids)
        log.info("%s: staged %d transactions", source.name, len(staging))
        return staging

    def _on_retry(self, source: Source, attempt: int, exc: BaseException, delay: float) -> None:
        log.warning("%s: attempt %d failed (%s); retrying in %.2fs", source.name, attempt, exc, delay)
