"""Config-driven deterministic policy evaluator for route scoring."""

from __future__ import annotations

from dataclasses import dataclass

from smart_router.core.policies.capability_matcher import CapabilityMatcher
from smart_router.core.policies.cost_optimizer import CostOptimizer
from smart_router.core.policies.latency_optimizer import LatencyOptimizer
from smart_router.core.policies.provider_health_selector import ProviderHealthSelector
from smart_router.core.router.schemas import ProviderHealthMetadata, RouterRuntimeContext
from smart_router.schemas.classification import PromptClassification
from smart_router.schemas.config import AppConfig, ModelConfig


@dataclass(frozen=True)
class ScoredCandidate:
    provider: str
    model: str
    capabilities: list[str]
    estimated_cost: float
    estimated_latency: float
    score: float


class RoutingPolicyEvaluator:
    """Evaluate provider/model candidates through deterministic policy layers."""

    def __init__(
        self,
        *,
        capability_matcher: CapabilityMatcher | None = None,
        cost_optimizer: CostOptimizer | None = None,
        latency_optimizer: LatencyOptimizer | None = None,
        health_selector: ProviderHealthSelector | None = None,
    ) -> None:
        self._cap = capability_matcher or CapabilityMatcher()
        self._cost = cost_optimizer or CostOptimizer()
        self._lat = latency_optimizer or LatencyOptimizer()
        self._health = health_selector or ProviderHealthSelector()

    def evaluate(
        self,
        *,
        classification: PromptClassification,
        runtime_context: RouterRuntimeContext,
        config: AppConfig,
        provider_health: ProviderHealthMetadata | None = None,
    ) -> list[ScoredCandidate]:
        candidates: list[ScoredCandidate] = []
        health_scores = provider_health.health_score if provider_health else {}

        for provider_name, provider_cfg in config.providers.items():
            if not provider_cfg.enabled:
                continue
            for model in provider_cfg.models:
                candidates.append(
                    self._score_candidate(
                        provider=provider_name,
                        model=model,
                        classification=classification,
                        runtime_context=runtime_context,
                        health_scores=health_scores,
                        routing_config=config,
                    )
                )

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    def _score_candidate(
        self,
        *,
        provider: str,
        model: ModelConfig,
        classification: PromptClassification,
        runtime_context: RouterRuntimeContext,
        health_scores: dict[str, float],
        routing_config: AppConfig,
    ) -> ScoredCandidate:
        cap_score = self._cap.score(classification, model)
        est_cost = self._cost.estimate_cost(classification, model)

        budget_limit = runtime_context.budget_limit
        if budget_limit is None:
            budget_limit = routing_config.routing.max_cost_per_request
        cost_score = self._cost.score(est_cost, budget_limit=budget_limit)

        est_latency = self._lat.estimate_latency(classification, model)
        latency_score = self._lat.score(classification, est_latency)
        health_score = self._health.score(provider, health_scores)

        # Config-driven weights with deterministic rules.
        weight_cap = 0.38
        weight_cost = 0.20
        weight_latency = 0.22
        weight_health = 0.20

        if routing_config.routing.prioritize_cost or runtime_context.prefers_low_cost:
            weight_cost += 0.10
            weight_cap -= 0.05
            weight_latency -= 0.05
        if routing_config.routing.prioritize_latency or runtime_context.prefers_low_latency:
            weight_latency += 0.10
            weight_cap -= 0.05
            weight_cost -= 0.05

        final_score = (
            (weight_cap * cap_score)
            + (weight_cost * cost_score)
            + (weight_latency * latency_score)
            + (weight_health * health_score)
        )

        return ScoredCandidate(
            provider=provider,
            model=model.name,
            capabilities=model.capabilities,
            estimated_cost=est_cost,
            estimated_latency=est_latency,
            score=max(0.0, min(1.0, final_score)),
        )
