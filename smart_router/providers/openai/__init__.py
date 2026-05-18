"""OpenAI provider adapter package."""

from smart_router.providers.openai.adapter import OpenAIProvider, register_openai_provider
from smart_router.providers.openai.exceptions import (
    OpenAIAuthError,
    OpenAIMalformedResponseError,
    OpenAIModelUnavailableError,
    OpenAIProviderError,
    OpenAIRateLimitError,
    OpenAITimeoutError,
    OpenAITransientError,
)
from smart_router.providers.openai.schemas import OpenAIProviderConfig, OpenAIStreamEvent

__all__ = [
    "OpenAIProvider",
    "OpenAIProviderConfig",
    "OpenAIStreamEvent",
    "OpenAIProviderError",
    "OpenAIAuthError",
    "OpenAIRateLimitError",
    "OpenAITimeoutError",
    "OpenAIModelUnavailableError",
    "OpenAIMalformedResponseError",
    "OpenAITransientError",
    "register_openai_provider",
]
