"""Cost optimization policy component."""

from __future__ import annotations

from smart_router.schemas.classification import PromptClassification
from smart_router.schemas.config import ModelConfig


class CostOptimizer:
    """Estimate costs and generate normalized affordability scores."""

    def estimate_cost(self, classification: PromptClassification, model: ModelConfig) -> float:
        input_cost = (classification.estimated_input_tokens / 1000.0) * model.cost_per_1k_input
        output_cost = (classification.estimated_output_tokens / 1000.0) * model.cost_per_1k_output
        return max(0.0, input_cost + output_cost)

    def score(self, estimated_cost: float, *, budget_limit: float | None) -> float:
        if budget_limit is not None and budget_limit > 0:
            if estimated_cost > budget_limit:
                return 0.0
            return max(0.0, 1.0 - (estimated_cost / budget_limit))

        # fallback normalized score without explicit budget
        return 1.0 / (1.0 + (estimated_cost * 8.0))
