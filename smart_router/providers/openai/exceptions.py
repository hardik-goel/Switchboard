"""Typed exceptions for OpenAI provider adapter."""

from __future__ import annotations


class OpenAIProviderError(RuntimeError):
    """Base OpenAI provider exception."""


class OpenAIAuthError(OpenAIProviderError):
    """Authentication failed for OpenAI API."""


class OpenAIRateLimitError(OpenAIProviderError):
    """OpenAI API rate limit was hit."""


class OpenAITimeoutError(OpenAIProviderError):
    """OpenAI request timed out."""


class OpenAIModelUnavailableError(OpenAIProviderError):
    """Requested OpenAI model is unavailable in current config."""


class OpenAIMalformedResponseError(OpenAIProviderError):
    """OpenAI API returned malformed/unexpected response payload."""


class OpenAITransientError(OpenAIProviderError):
    """Transient OpenAI failure that may be retried safely."""
