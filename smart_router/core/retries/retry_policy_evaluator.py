"""Retry policy evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from smart_router.core.retries.failure_classifier import FailureClassification


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 2
    base_backoff_seconds: float = 0.2
    exponential_factor: float = 2.0


class RetryPolicyEvaluator:
    """Evaluate whether a failure should be retried."""

    def should_retry(self, *, failure: FailureClassification, retry_count: int, policy: RetryPolicy) -> bool:
        if not failure.retryable:
            return False
        return retry_count < policy.max_retries

    def backoff_seconds(self, *, retry_count: int, policy: RetryPolicy) -> float:
        return policy.base_backoff_seconds * (policy.exponential_factor ** max(0, retry_count - 1))
