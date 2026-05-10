"""Prompt analyzer input schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RepoMetadata(BaseModel):
    """Optional repository-level metadata used for heuristics."""

    file_count: int | None = Field(default=None, ge=0)
    language_breakdown: dict[str, int] = Field(default_factory=dict)
    has_ci: bool | None = None


class FileMetadata(BaseModel):
    """Optional file-level metadata signals."""

    changed_files: list[str] = Field(default_factory=list)
    touched_directories: list[str] = Field(default_factory=list)


class AnalyzerExecutionContext(BaseModel):
    """Optional runtime context for analysis."""

    request_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
