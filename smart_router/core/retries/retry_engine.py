"""Retry engine with deterministic backoff and cancellation awareness."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from smart_router.core.retries.failure_classifier import FailureClassification
from smart_router.core.retries.retry_policy_evaluator import RetryPolicy, RetryPolicyEvaluator


class RetryEngine:
    """Execute retry lifecycle using failure classification and policy evaluator."""

    def __init__(self, evaluator: RetryPolicyEvaluator | None = None) -> None:
        self._evaluator = evaluator or RetryPolicyEvaluator()

    async def run(
        self,
        *,
        operation: Callable[[], Awaitable[object]],
        classify_failure: Callable[[Exception], FailureClassification],
        policy: RetryPolicy,
        on_retry: Callable[[int, FailureClassification], Awaitable[None]] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> object:
        retry_count = 0

        while True:
            if is_cancelled and is_cancelled():
                raise asyncio.CancelledError()
            try:
                return await operation()
            except Exception as exc:
                failure = classify_failure(exc)
                retry_count += 1
                if not self._evaluator.should_retry(failure=failure, retry_count=retry_count, policy=policy):
                    raise
                if on_retry is not None:
                    await on_retry(retry_count, failure)
                await asyncio.sleep(self._evaluator.backoff_seconds(retry_count=retry_count, policy=policy))
