"""OpenAI provider-specific configuration and payload schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, SecretStr


class OpenAIProviderConfig(BaseModel):
    """Typed OpenAI config derived from app provider config + env vars."""

    provider_name: str = Field(default="openai")
    api_key: SecretStr
    api_base: str = Field(default="https://api.openai.com/v1")
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=2, ge=0, le=10)
    default_model: str | None = None
    enabled_models: set[str] = Field(default_factory=set)


class OpenAIChatMessage(BaseModel):
    """OpenAI-compatible chat message shape."""

    role: str
    content: str


class OpenAIChatRequest(BaseModel):
    """OpenAI chat completion request envelope."""

    model: str
    messages: list[OpenAIChatMessage]
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    stream: bool = False


class OpenAIStreamEvent(BaseModel):
    """Provider-agnostic normalized stream event emitted by OpenAI adapter."""

    event_type: str
    provider: str
    model: str
    request_id: str
    content_delta: str = ""
    done: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
