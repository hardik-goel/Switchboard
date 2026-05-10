"""Typed exceptions for Anthropic provider adapter."""

from __future__ import annotations


class AnthropicProviderError(RuntimeError):
    """Base Anthropic provider error."""


class AnthropicAuthError(AnthropicProviderError):
    """Anthropic authentication failure."""


class AnthropicRateLimitError(AnthropicProviderError):
    """Anthropic rate limit exceeded."""


class AnthropicTimeoutError(AnthropicProviderError):
    """Anthropic request timed out."""


class AnthropicModelUnavailableError(AnthropicProviderError):
    """Requested Anthropic model is unavailable."""


class AnthropicMalformedResponseError(AnthropicProviderError):
    """Anthropic returned malformed payload."""


class AnthropicTransientError(AnthropicProviderError):
    """Transient Anthropic failure, retry-safe."""
