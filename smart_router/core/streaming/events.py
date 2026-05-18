"""Provider-agnostic stream event schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

StreamEventType = Literal[
    "stream_started",
    "token_chunk",
    "stream_completed",
    "stream_interrupted",
    "provider_error",
]


class StreamEvent(BaseModel):
    """Normalized stream lifecycle event."""

    event_type: StreamEventType
    request_id: str
    session_id: str | None = None
    provider: str
    model: str
    content: str = ""
    retry_count: int = 0
    stream_state: str = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)
