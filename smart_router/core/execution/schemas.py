"""Execution integration schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from smart_router.core.orchestrator.schemas import ExecutionRequest, ExecutionResult
from smart_router.schemas.provider import ProviderMessage
from smart_router.schemas.routing import RoutingDecision

ExecutionState = Literal[
    "pending",
    "running",
    "retrying",
    "fallback_active",
    "interrupted",
    "completed",
    "failed",
]


class ExecutionPlan(BaseModel):
    """Executable plan derived from routing decision."""

    request_id: str
    session_id: str | None = None
    primary_provider: str
    primary_model: str
    fallback_chain: list[str] = Field(default_factory=list)
    execution_strategy: str
    timeout_seconds: float | None = Field(default=None, gt=0)
    messages: list[ProviderMessage] = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


class LifecycleSnapshot(BaseModel):
    """Execution lifecycle state snapshot."""

    request_id: str
    session_id: str | None
    state: ExecutionState
    retry_count: int = Field(default=0, ge=0)
    active_provider: str
    active_model: str
    fallback_provider: str | None = None
    failure_type: str | None = None


class FinalExecutionOutcome(BaseModel):
    """Normalized final execution outcome."""

    snapshot: LifecycleSnapshot
    result: ExecutionResult | None = None
    failure_reason: str | None = None
