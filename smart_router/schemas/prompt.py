"""Prompt input schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PromptRequest(BaseModel):
    """User prompt request entering the routing pipeline."""

    prompt: str = Field(min_length=1)
    session_id: str | None = None
    user_preferences: dict[str, str] = Field(default_factory=dict)
