"""Runtime execution context models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CancellationState(BaseModel):
    """Mutable cancellation state for a request lifecycle."""

    is_cancelled: bool = False
    reason: str | None = None


class StreamState(BaseModel):
    """Streaming state for runtime lifecycle."""

    is_streaming: bool = False
    is_completed: bool = False
    last_event_type: str | None = None


class RuntimeExecutionContext(BaseModel):
    """Provider execution runtime context shared across orchestrator modules."""

    request_id: str
    session_id: str | None = None
    selected_provider: str
    selected_model: str
    retry_count: int = Field(default=0, ge=0)
    cancellation_state: CancellationState = Field(default_factory=CancellationState)
    stream_state: StreamState = Field(default_factory=StreamState)
    token_estimates: dict[str, int] = Field(default_factory=dict)
    execution_metadata: dict[str, Any] = Field(default_factory=dict)
