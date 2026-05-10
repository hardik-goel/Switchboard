"""Map routing outputs to orchestrator-compatible execution requests."""

from __future__ import annotations

from smart_router.core.orchestrator.schemas import ExecutionRequest

from .schemas import ExecutionPlan


class RouteExecutionMapper:
    """Translate execution plan into orchestrator execution request."""

    def to_execution_request(self, plan: ExecutionPlan, *, provider: str, model: str) -> ExecutionRequest:
        return ExecutionRequest(
            request_id=plan.request_id,
            provider=provider,
            model=model,
            messages=plan.messages,
            temperature=plan.temperature,
            timeout_seconds=plan.timeout_seconds,
            stream=False,
            session_id=plan.session_id,
        )
