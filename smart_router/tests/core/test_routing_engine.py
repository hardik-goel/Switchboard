from __future__ import annotations

from pathlib import Path

import pytest

from smart_router.core.analyzer import PromptAnalyzer
from smart_router.core.config import ConfigEngine
from smart_router.core.policies import CapabilityMatcher, RoutingPolicyEvaluator
from smart_router.core.router import ProviderHealthMetadata, RouterRuntimeContext, RoutingEngine
from smart_router.schemas.prompt import PromptRequest
from smart_router.schemas.config import ModelConfig


@pytest.fixture
def routing_engine() -> RoutingEngine:
    engine = ConfigEngine(Path("smart_router/configs/default.yaml"))
    config = engine.load()
    return RoutingEngine(config)


@pytest.mark.asyncio
async def test_low_complexity_routing(routing_engine: RoutingEngine) -> None:
    analyzer = PromptAnalyzer()
    classification = await analyzer.analyze("rename variable in one file")
    decision = await routing_engine.choose_route(PromptRequest(prompt="x"), classification)
    assert decision.selected_provider
    assert decision.selected_model
    assert decision.routing_confidence >= 0.0


@pytest.mark.asyncio
async def test_high_complexity_routing(routing_engine: RoutingEngine) -> None:
    analyzer = PromptAnalyzer()
    classification = await analyzer.analyze("architecture redesign for auth concurrency across codebase")
    decision = await routing_engine.choose_route(PromptRequest(prompt="x"), classification)
    assert decision.execution_strategy == "staged_execution_with_validation"
    assert "complexity=high" in decision.reasoning_summary


@pytest.mark.asyncio
async def test_repo_wide_routing(routing_engine: RoutingEngine) -> None:
    analyzer = PromptAnalyzer()
    classification = await analyzer.analyze("migrate repo-wide dependencies across all files")
    decision = await routing_engine.choose_route(PromptRequest(prompt="x"), classification)
    assert decision.execution_strategy == "staged_execution_with_validation"


@pytest.mark.asyncio
async def test_budget_sensitive_routing(routing_engine: RoutingEngine) -> None:
    analyzer = PromptAnalyzer()
    classification = await analyzer.analyze("refactor service logic")
    decision = await routing_engine.choose_route(
        PromptRequest(prompt="x"),
        classification,
        runtime_context=RouterRuntimeContext(budget_limit=0.001, prefers_low_cost=True),
    )
    assert decision.estimated_cost >= 0.0


@pytest.mark.asyncio
async def test_latency_sensitive_routing(routing_engine: RoutingEngine) -> None:
    analyzer = PromptAnalyzer()
    classification = await analyzer.analyze("urgent hotfix fix broken endpoint quickly")
    decision = await routing_engine.choose_route(
        PromptRequest(prompt="x"),
        classification,
        runtime_context=RouterRuntimeContext(prefers_low_latency=True),
    )
    assert decision.execution_strategy in ("fast_path", "standard")


@pytest.mark.asyncio
async def test_fallback_chain_generation(routing_engine: RoutingEngine) -> None:
    analyzer = PromptAnalyzer()
    classification = await analyzer.analyze("add endpoint")
    decision = await routing_engine.choose_route(PromptRequest(prompt="x"), classification)
    assert isinstance(decision.fallback_chain, list)


@pytest.mark.asyncio
async def test_provider_health_affects_routing(routing_engine: RoutingEngine) -> None:
    analyzer = PromptAnalyzer()
    classification = await analyzer.analyze("debug failing test")
    decision = await routing_engine.choose_route(
        PromptRequest(prompt="x"),
        classification,
        provider_health=ProviderHealthMetadata(health_score={"openai": 0.1, "anthropic": 1.0}),
    )
    assert decision.selected_provider in ("openai", "anthropic")


@pytest.mark.asyncio
async def test_capability_matcher_scoring() -> None:
    analyzer = PromptAnalyzer()
    classification = await analyzer.analyze("architecture redesign with repo search")
    matcher = CapabilityMatcher()
    model = ModelConfig(
        name="test-model",
        max_input_tokens=128000,
        max_output_tokens=4096,
        latency_tier="medium",
        reasoning_tier="high",
        cost_per_1k_input=0.01,
        cost_per_1k_output=0.02,
        capabilities=["long_context_reasoning", "repo_search", "planning"],
    )
    score = matcher.score(classification, model)
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_policy_evaluator_returns_ranked_candidates() -> None:
    engine = ConfigEngine(Path("smart_router/configs/default.yaml"))
    config = engine.load()
    evaluator = RoutingPolicyEvaluator()

    classification = await PromptAnalyzer().analyze("large refactor")

    candidates = evaluator.evaluate(
        classification=classification,
        runtime_context=RouterRuntimeContext(),
        config=config,
    )
    assert candidates
    assert candidates[0].score >= candidates[-1].score
