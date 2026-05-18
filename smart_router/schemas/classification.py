"""Prompt analysis and classification schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ReasoningDepth = Literal["low", "medium", "high"]
ComplexityLevel = Literal["low", "medium", "high"]
RepoScope = Literal["single_file", "multi_file", "repo_wide", "architectural"]
TaskType = Literal[
    "bugfix",
    "refactor",
    "feature",
    "debugging",
    "migration",
    "architecture",
    "documentation",
    "testing",
    "unknown",
]
ExecutionRiskLevel = Literal["low", "medium", "high"]
LatencySensitivity = Literal["low", "medium", "high"]


class PromptClassification(BaseModel):
    """Structured prompt intelligence output for future routing consumption."""

    complexity_level: ComplexityLevel
    complexity_score: float = Field(ge=0.0, le=1.0)
    reasoning_depth: ReasoningDepth
    estimated_input_tokens: int = Field(ge=0)
    estimated_output_tokens: int = Field(ge=0)
    estimated_total_tokens: int = Field(ge=0)
    context_expansion_tokens: int = Field(ge=0)
    repo_scope: RepoScope
    latency_sensitivity: LatencySensitivity
    task_type: TaskType
    confidence_score: float = Field(ge=0.0, le=1.0)
    suggested_capabilities: list[str] = Field(default_factory=list)
    execution_risk_level: ExecutionRiskLevel

    # Backward-compatible convenience fields from early scaffold.
    latency_sensitive: bool = False
    repo_wide_operation: bool = False
