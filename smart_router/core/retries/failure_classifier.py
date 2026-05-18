"""Failure classification for retry and fallback decisions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FailureClassification:
    failure_type: str
    retryable: bool


class FailureClassifier:
    """Classify failures into deterministic retry/fallback categories."""

    def classify(self, exc: Exception) -> FailureClassification:
        name = exc.__class__.__name__.lower()
        message = str(exc).lower()

        if "auth" in name or "unauthorized" in message or "forbidden" in message:
            return FailureClassification("auth_failure", False)
        if "timeout" in name or "timeout" in message:
            return FailureClassification("timeout_failure", True)
        if "ratelimit" in name or "rate limit" in message or "429" in message:
            return FailureClassification("rate_limit", True)
        if "unavailable" in name or "not found" in message or "providerunavailable" in name:
            return FailureClassification("provider_unavailable", True)
        if "malformed" in name:
            return FailureClassification("malformed_response", False)
        if "transient" in name or "transport" in message or "server error" in message:
            return FailureClassification("transient_failure", True)
        return FailureClassification("unknown_failure", False)
