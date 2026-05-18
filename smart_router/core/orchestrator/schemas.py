"""Orchestrator request/result abstractions."""

from __future__ import annotations

from pydantic import BaseModel, Field

from smart_router.schemas.provider import ProviderMessage, ProviderResponse


class ExecutionRequest(BaseModel):
    """Normalized provider execution request from upstream decision layer."""

    request_id: str | None = None
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    messages: list[ProviderMessage] = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    timeout_seconds: float | None = Field(default=None, gt=0)
    stream: bool = False
    session_id: str | None = None
    token_estimates: dict[str, int] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    """Final orchestrated non-streaming execution output."""

    request_id: str
    provider: str
    model: str
    response: ProviderResponse
    latency_ms: int = Field(ge=0)
    retry_count: int = Field(ge=0)
