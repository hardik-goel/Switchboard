from __future__ import annotations

import pytest
from pydantic import ValidationError

from smart_router.schemas.classification import PromptClassification
from smart_router.schemas.prompt import PromptRequest
from smart_router.schemas.routing import RoutingDecision


def test_prompt_request_requires_prompt() -> None:
    with pytest.raises(ValidationError):
        PromptRequest(prompt="")


def test_classification_score_bounds() -> None:
    with pytest.raises(ValidationError):
        PromptClassification(
            complexity_level="medium",
            complexity_score=1.5,
            reasoning_depth="high",
            estimated_input_tokens=10,
            estimated_output_tokens=20,
            estimated_total_tokens=30,
            context_expansion_tokens=2,
            repo_scope="multi_file",
            latency_sensitivity="low",
            task_type="refactor",
            confidence_score=0.6,
            suggested_capabilities=["code_editing"],
            execution_risk_level="medium",
        )


def test_routing_decision_requires_provider_model_reason() -> None:
    decision = RoutingDecision(provider="openai", model="gpt-5.4", reason="latency")
    assert decision.provider == "openai"
    assert decision.model == "gpt-5.4"
