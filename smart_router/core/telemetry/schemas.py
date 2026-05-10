"""Telemetry event schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

TelemetryEventType = Literal[
    "execution_started",
    "execution_completed",
    "execution_failed",
    "retry_triggered",
    "fallback_triggered",
    "route_selected",
    "provider_degraded",
    "stream_interrupted",
]


class TelemetryEvent(BaseModel):
    """Normalized telemetry event envelope."""

    event_type: TelemetryEventType
    request_id: str | None = None
    session_id: str | None = None
    provider: str | None = None
    model: str | None = None
    latency: float | None = None
    cost_estimate: float | None = None
    retry_count: int = 0
    fallback_count: int = 0
    execution_state: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
