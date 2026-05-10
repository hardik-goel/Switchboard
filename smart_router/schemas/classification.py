"""Prompt classification schema."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ReasoningDepth = Literal["low", "medium", "high"]


class PromptClassification(BaseModel):
    """Computed prompt analysis metadata used by routing."""

    complexity_score: float = Field(ge=0.0, le=1.0)
    estimated_input_tokens: int = Field(ge=0)
    estimated_output_tokens: int = Field(ge=0)
    reasoning_depth: ReasoningDepth
    latency_sensitive: bool = False
    repo_wide_operation: bool = False
