"""Session and persistence schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SessionState = Literal[
    "session_created",
    "execution_running",
    "retrying",
    "fallback_active",
    "interrupted",
    "resumable",
    "resumed",
    "completed",
    "failed",
    "archived",
]


class SessionRecord(BaseModel):
    """Persistent session metadata."""

    session_id: str
    request_id: str
    lifecycle_state: SessionState = "session_created"
    provider: str | None = None
    model: str | None = None
    retry_count: int = 0
    fallback_count: int = 0
    recovery_state: str | None = None
    telemetry_references: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StateTransitionRecord(BaseModel):
    """Persistent execution state transition."""

    session_id: str
    request_id: str
    lifecycle_state: SessionState
    provider: str | None = None
    model: str | None = None
    retry_count: int = 0
    fallback_count: int = 0
    recovery_state: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextSnapshot(BaseModel):
    """Recoverable context snapshot payload."""

    session_id: str
    request_id: str
    snapshot_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
