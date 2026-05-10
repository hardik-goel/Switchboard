"""Provider message and response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProviderMessage(BaseModel):
    """Single role/content message normalized across providers."""

    role: str = Field(min_length=1)
    content: str = Field(min_length=1)


class ProviderResponse(BaseModel):
    """Normalized provider response envelope."""

    content: str = Field(min_length=1)
    model: str = Field(min_length=1)
    usage: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
