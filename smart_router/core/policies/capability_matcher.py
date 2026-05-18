"""Capability matching policy component."""

from __future__ import annotations

from smart_router.schemas.classification import PromptClassification
from smart_router.schemas.config import ModelConfig


class CapabilityMatcher:
    """Score how well a model capability profile matches task needs."""

    def score(self, classification: PromptClassification, model: ModelConfig) -> float:
        score = 0.0
        required = set(classification.suggested_capabilities)
        offered = set(model.capabilities)

        if required:
            coverage = len(required.intersection(offered)) / len(required)
            score += 0.45 * coverage

        if classification.reasoning_depth == "high" and model.reasoning_tier == "high":
            score += 0.25
        elif classification.reasoning_depth == "medium" and model.reasoning_tier in ("medium", "high"):
            score += 0.18

        if classification.estimated_total_tokens <= model.context_window:
            score += 0.20

        if classification.repo_scope in ("repo_wide", "architectural") and model.context_window >= 128000:
            score += 0.10

        return min(1.0, score)
