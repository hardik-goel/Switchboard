"""Deterministic routing engine consuming structured PromptClassification."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from smart_router.core.policies.fallback_planner import Candidate, FallbackPlanner
from smart_router.core.policies.routing_policy_evaluator import RoutingPolicyEvaluator
from smart_router.core.router.schemas import ProviderHealthMetadata, RouterRuntimeContext
from smart_router.core.telemetry import maybe_emit
from smart_router.schemas.classification import PromptClassification
from smart_router.schemas.config import AppConfig
from smart_router.schemas.prompt import PromptRequest
from smart_router.schemas.routing import RoutingDecision

logger = logging.getLogger("smart_router.router.engine")
TelemetryHook = Callable[[dict[str, Any]], Awaitable[None] | None]


class RoutingEngine:
    """Choose provider/model deterministically from policy-evaluated candidates."""

    def __init__(
        self,
        config: AppConfig,
        *,
        policy_evaluator: RoutingPolicyEvaluator | None = None,
        fallback_planner: FallbackPlanner | None = None,
        telemetry_hook: TelemetryHook | None = None,
    ) -> None:
        self._config = config
        self._policy = policy_evaluator or RoutingPolicyEvaluator()
        self._fallback = fallback_planner or FallbackPlanner()
        self._telemetry_hook = telemetry_hook

    async def choose_route(
        self,
        request: PromptRequest,
        classification: PromptClassification,
        *,
        runtime_context: RouterRuntimeContext | None = None,
        provider_health: ProviderHealthMetadata | None = None,
    ) -> RoutingDecision:
        context = runtime_context or RouterRuntimeContext(session_id=request.session_id)
        candidates = self._policy.evaluate(
            classification=classification,
            runtime_context=context,
            config=self._config,
            provider_health=provider_health,
        )

        if not candidates:
            raise RuntimeError("No routing candidates available from configuration.")

        selected = candidates[0]
        fallback_chain = self._fallback.plan(
            selected=Candidate(selected.provider, selected.model, selected.score),
            ranked=[Candidate(c.provider, c.model, c.score) for c in candidates],
            max_items=3,
        )

        confidence = max(0.0, min(1.0, selected.score * classification.confidence_score))
        execution_strategy = self._execution_strategy(classification)
        reason = self._reasoning_summary(selected.provider, selected.model, classification, selected)

        decision = RoutingDecision(
            selected_provider=selected.provider,
            selected_model=selected.model,
            reasoning_summary=reason,
            fallback_chain=fallback_chain,
            estimated_cost=selected.estimated_cost,
            estimated_latency=selected.estimated_latency,
            routing_confidence=confidence,
            selected_capabilities=selected.capabilities,
            execution_strategy=execution_strategy,
            provider=selected.provider,
            model=selected.model,
            reason=reason,
        )

        logger.info(
            "route_selected",
            extra={
                "request_id": context.request_id,
                "session_id": context.session_id,
                "selected_provider": decision.selected_provider,
                "selected_model": decision.selected_model,
                "routing_confidence": decision.routing_confidence,
                "estimated_cost": decision.estimated_cost,
                "estimated_latency": decision.estimated_latency,
                "fallback_count": len(decision.fallback_chain),
            },
        )
        await maybe_emit(
            self._telemetry_hook,
            {
                "event_type": "route_selected",
                "request_id": context.request_id,
                "session_id": context.session_id,
                "provider": decision.selected_provider,
                "model": decision.selected_model,
                "latency": decision.estimated_latency,
                "cost_estimate": decision.estimated_cost,
                "fallback_count": len(decision.fallback_chain),
                "execution_state": "selected",
                "metadata": {"routing_confidence": decision.routing_confidence},
            },
        )
        return decision

    def _reasoning_summary(
        self,
        provider: str,
        model: str,
        classification: PromptClassification,
        candidate,
    ) -> str:
        return (
            f"Selected {provider}:{model} because it scored highest for "
            f"complexity={classification.complexity_level}, scope={classification.repo_scope}, "
            f"latency={classification.latency_sensitivity}, cost≈{candidate.estimated_cost:.4f}."
        )

    def _execution_strategy(self, classification: PromptClassification) -> str:
        if classification.repo_scope in ("repo_wide", "architectural"):
            return "staged_execution_with_validation"
        if classification.latency_sensitivity == "high":
            return "fast_path"
        return "standard"
