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


def test_routing_decision_requires_structured_fields() -> None:
    decision = RoutingDecision(
        selected_provider="openai",
        selected_model="gpt-5.4",
        reasoning_summary="selected due to latency",
        fallback_chain=["anthropic:claude-sonnet"],
        estimated_cost=0.12,
        estimated_latency=1800.0,
        routing_confidence=0.82,
        selected_capabilities=["code_editing"],
        execution_strategy="standard",
    )
    assert decision.selected_provider == "openai"
    assert decision.selected_model == "gpt-5.4"
