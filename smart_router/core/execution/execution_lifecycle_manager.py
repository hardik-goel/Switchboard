"""Execution lifecycle coordinator for retries and fallback transitions."""

from __future__ import annotations

import asyncio
import logging
import time

from smart_router.core.execution.route_execution_mapper import RouteExecutionMapper
from smart_router.core.execution.schemas import ExecutionPlan, FinalExecutionOutcome, LifecycleSnapshot
from smart_router.core.fallbacks.fallback_execution_manager import FallbackExecutionManager
from smart_router.core.orchestrator import ProviderOrchestrator
from smart_router.core.orchestrator.exceptions import ExecutionFailureError
from smart_router.core.orchestrator.schemas import ExecutionResult
from smart_router.core.retries.failure_classifier import FailureClassifier
from smart_router.core.retries.retry_engine import RetryEngine
from smart_router.core.retries.retry_policy_evaluator import RetryPolicy

logger = logging.getLogger("smart_router.execution.lifecycle")


class ExecutionLifecycleManager:
    """Coordinate execution, retries, and fallback failover lifecycle."""

    def __init__(
        self,
        orchestrator: ProviderOrchestrator,
        *,
        mapper: RouteExecutionMapper | None = None,
        retry_engine: RetryEngine | None = None,
        fallback_manager: FallbackExecutionManager | None = None,
        failure_classifier: FailureClassifier | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._mapper = mapper or RouteExecutionMapper()
        self._retry_engine = retry_engine or RetryEngine()
        self._fallback = fallback_manager or FallbackExecutionManager(self._mapper)
        self._classifier = failure_classifier or FailureClassifier()
        self._retry_policy = retry_policy or RetryPolicy()
        self._cancelled: set[str] = set()

    def cancel(self, request_id: str) -> None:
        self._cancelled.add(request_id)
        self._orchestrator.cancel(request_id, reason="execution_cancelled")

    async def execute(self, plan: ExecutionPlan) -> FinalExecutionOutcome:
        snapshot = LifecycleSnapshot(
            request_id=plan.request_id,
            session_id=plan.session_id,
            state="pending",
            active_provider=plan.primary_provider,
            active_model=plan.primary_model,
        )

        start = time.perf_counter()
        try:
            primary_request = self._mapper.to_execution_request(
                plan,
                provider=plan.primary_provider,
                model=plan.primary_model,
            )
            snapshot.state = "running"
            result = await self._execute_with_retry(primary_request, snapshot)
            snapshot.state = "completed"
            return FinalExecutionOutcome(snapshot=snapshot, result=result)
        except Exception as primary_exc:
            failure = self._classifier.classify(primary_exc)
            snapshot.failure_type = failure.failure_type
            fallback_targets = self._fallback.parse_chain(plan.fallback_chain)

            for target in fallback_targets:
                snapshot.state = "fallback_active"
                snapshot.fallback_provider = target.provider
                snapshot.active_provider = target.provider
                snapshot.active_model = target.model
                fallback_request = self._fallback.build_request(plan=plan, target=target)
                try:
                    result = await self._execute_with_retry(fallback_request, snapshot)
                    snapshot.state = "completed"
                    return FinalExecutionOutcome(snapshot=snapshot, result=result)
                except Exception as fallback_exc:
                    failure = self._classifier.classify(fallback_exc)
                    snapshot.failure_type = failure.failure_type
                    continue

            snapshot.state = "failed"
            return FinalExecutionOutcome(
                snapshot=snapshot,
                result=None,
                failure_reason=str(primary_exc),
            )
        finally:
            latency = int((time.perf_counter() - start) * 1000)
            logger.info(
                "execution_lifecycle_completed",
                extra={
                    "request_id": snapshot.request_id,
                    "session_id": snapshot.session_id,
                    "retry_count": snapshot.retry_count,
                    "active_provider": snapshot.active_provider,
                    "fallback_provider": snapshot.fallback_provider,
                    "failure_type": snapshot.failure_type,
                    "lifecycle_state": snapshot.state,
                    "latency": latency,
                },
            )

    async def _execute_with_retry(self, request, snapshot: LifecycleSnapshot) -> ExecutionResult:
        async def operation():
            if request.request_id in self._cancelled:
                raise asyncio.CancelledError()
            return await self._orchestrator.execute(request)

        async def on_retry(retry_count, failure):
            snapshot.retry_count = retry_count
            snapshot.failure_type = failure.failure_type
            snapshot.state = "retrying"

        def is_cancelled() -> bool:
            return request.request_id in self._cancelled

        try:
            result = await self._retry_engine.run(
                operation=operation,
                classify_failure=self._classifier.classify,
                policy=self._retry_policy,
                on_retry=on_retry,
                is_cancelled=is_cancelled,
            )
            snapshot.state = "running"
            if isinstance(result, ExecutionResult):
                return result
            raise ExecutionFailureError("Unexpected execution result type.")
        except asyncio.CancelledError as exc:
            snapshot.state = "interrupted"
            raise ExecutionFailureError("Execution cancelled.") from exc
