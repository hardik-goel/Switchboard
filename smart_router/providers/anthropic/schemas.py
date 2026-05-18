"""Anthropic provider-specific schemas and normalized stream payload."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, SecretStr


class AnthropicProviderConfig(BaseModel):
    """Typed Anthropic provider config."""

    provider_name: str = Field(default="anthropic")
    api_key: SecretStr
    api_base: str = Field(default="https://api.anthropic.com/v1")
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=2, ge=0, le=10)
    default_model: str | None = None
    enabled_models: set[str] = Field(default_factory=set)


class AnthropicMessageItem(BaseModel):
    """Anthropic message item."""

    role: str
    content: str


class AnthropicGenerateRequest(BaseModel):
    """Anthropic messages API request payload."""

    model: str
    max_tokens: int = Field(default=1024, ge=1)
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    messages: list[AnthropicMessageItem]
    stream: bool = False


class AnthropicStreamEvent(BaseModel):
    """Provider-agnostic normalized stream event payload from Anthropic adapter."""

    event_type: str
    provider: str
    model: str
    request_id: str
    content_delta: str = ""
    done: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
