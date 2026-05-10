"""Routing runtime support schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RouterRuntimeContext(BaseModel):
    """Optional runtime context used by routing policies."""

    request_id: str | None = None
    session_id: str | None = None
    budget_limit: float | None = Field(default=None, ge=0.0)
    prefers_low_latency: bool = False
    prefers_low_cost: bool = False


class ProviderHealthMetadata(BaseModel):
    """Provider health snapshot for routing-time filtering."""

    health_score: dict[str, float] = Field(default_factory=dict)
