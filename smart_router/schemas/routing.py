"""Routing decision schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RoutingDecision(BaseModel):
    """Deterministic routing output consumed by orchestration layer."""

    selected_provider: str = Field(min_length=1)
    selected_model: str = Field(min_length=1)
    reasoning_summary: str = Field(min_length=1)
    fallback_chain: list[str] = Field(default_factory=list)
    estimated_cost: float = Field(ge=0.0)
    estimated_latency: float = Field(ge=0.0)
    routing_confidence: float = Field(ge=0.0, le=1.0)
    selected_capabilities: list[str] = Field(default_factory=list)
    execution_strategy: str = Field(min_length=1)

    # Backward-compatible aliases from early scaffold.
    provider: str | None = None
    model: str | None = None
    reason: str | None = None
