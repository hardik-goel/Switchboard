"""Build executable plans from routing decisions."""

from __future__ import annotations

from smart_router.schemas.provider import ProviderMessage
from smart_router.schemas.routing import RoutingDecision

from .schemas import ExecutionPlan


class ExecutionPlanner:
    """Convert route decisions into executable runtime plans."""

    def create_plan(
        self,
        *,
        request_id: str,
        session_id: str | None,
        decision: RoutingDecision,
        messages: list[ProviderMessage],
        timeout_seconds: float | None = None,
        temperature: float = 0.0,
    ) -> ExecutionPlan:
        return ExecutionPlan(
            request_id=request_id,
            session_id=session_id,
            primary_provider=decision.selected_provider,
            primary_model=decision.selected_model,
            fallback_chain=decision.fallback_chain,
            execution_strategy=decision.execution_strategy,
            timeout_seconds=timeout_seconds,
            messages=messages,
            temperature=temperature,
        )
