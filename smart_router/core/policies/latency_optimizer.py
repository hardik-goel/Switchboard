"""Latency optimization policy component."""

from __future__ import annotations

from smart_router.schemas.classification import PromptClassification
from smart_router.schemas.config import ModelConfig


class LatencyOptimizer:
    """Estimate latency and provide normalized speed score."""

    _BASE_MS = {"fast": 900.0, "medium": 1800.0, "slow": 3200.0, "balanced": 1700.0}

    def estimate_latency(self, classification: PromptClassification, model: ModelConfig) -> float:
        tier = model.speed_class if model.speed_class in self._BASE_MS else model.latency_tier
        base = self._BASE_MS.get(tier, 1800.0)
        complexity_factor = 1.0 + classification.complexity_score
        token_factor = 1.0 + (classification.estimated_total_tokens / 120000.0)
        return base * complexity_factor * token_factor

    def score(self, classification: PromptClassification, estimated_latency: float) -> float:
        if classification.latency_sensitivity == "high":
            target = 2200.0
        elif classification.latency_sensitivity == "medium":
            target = 3200.0
        else:
            target = 5200.0
        return max(0.0, min(1.0, target / max(estimated_latency, 1.0)))
