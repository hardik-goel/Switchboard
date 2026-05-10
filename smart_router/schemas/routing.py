"""Routing decision schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RoutingDecision(BaseModel):
    """Deterministic routing output consumed by orchestration layer."""

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    fallback_chain: list[str] = Field(default_factory=list)
