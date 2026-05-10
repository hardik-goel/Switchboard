"""Typed orchestration/runtime exceptions."""

from __future__ import annotations


class OrchestrationError(RuntimeError):
    """Base orchestration exception."""


class InvalidExecutionRequestError(OrchestrationError):
    """Execution request failed validation checks."""


class ProviderUnavailableError(OrchestrationError):
    """Requested provider was unavailable or unresolved."""


class ExecutionFailureError(OrchestrationError):
    """Execution failed after retries or provider errors."""


class StreamFailureError(OrchestrationError):
    """Streaming execution failed."""


class RuntimeCancellationError(OrchestrationError):
    """Execution was cancelled by runtime lifecycle."""
