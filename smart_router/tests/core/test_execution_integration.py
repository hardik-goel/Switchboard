from __future__ import annotations

import asyncio

import pytest

from smart_router.core.execution import ExecutionLifecycleManager, ExecutionPlanner, RouteExecutionMapper
from smart_router.core.execution.schemas import ExecutionPlan
from smart_router.core.fallbacks import FallbackExecutionManager
from smart_router.core.orchestrator.schemas import ExecutionResult
from smart_router.core.retries import FailureClassifier, RetryEngine, RetryPolicy, RetryPolicyEvaluator
from smart_router.schemas.provider import ProviderMessage, ProviderResponse
from smart_router.schemas.routing import RoutingDecision


class MockOrchestrator:
    def __init__(self, responses: list[object]) -> None:
        self._responses = responses
        self.calls = 0
        self.cancelled: set[str] = set()

    async def execute(self, request):
        self.calls += 1
        item = self._responses[min(self.calls - 1, len(self._responses) - 1)]
        if isinstance(item, Exception):
            raise item
        if isinstance(item, ExecutionResult):
            return item
        raise RuntimeError("invalid mock response")

    def cancel(self, request_id: str, *, reason: str = "cancelled") -> None:
        _ = reason
        self.cancelled.add(request_id)


def _decision() -> RoutingDecision:
    return RoutingDecision(
        selected_provider="openai",
        selected_model="gpt-5.4",
        reasoning_summary="best",
        fallback_chain=["anthropic:claude-sonnet"],
        estimated_cost=0.1,
        estimated_latency=1000,
        routing_confidence=0.8,
        selected_capabilities=["code_editing"],
        execution_strategy="standard",
    )


def _messages() -> list[ProviderMessage]:
    return [ProviderMessage(role="user", content="hello")]


def _result(request_id: str, provider: str, model: str) -> ExecutionResult:
    return ExecutionResult(
        request_id=request_id,
        provider=provider,
        model=model,
        response=ProviderResponse(content="ok", model=model),
        latency_ms=100,
        retry_count=0,
    )


def test_execution_planner_creates_plan() -> None:
    planner = ExecutionPlanner()
    plan = planner.create_plan(
        request_id="req-1",
        session_id="sess-1",
        decision=_decision(),
        messages=_messages(),
        timeout_seconds=2.0,
    )
    assert plan.primary_provider == "openai"
    assert plan.fallback_chain == ["anthropic:claude-sonnet"]


def test_route_execution_mapper_maps_to_request() -> None:
    planner = ExecutionPlanner()
    mapper = RouteExecutionMapper()
    plan = planner.create_plan(
        request_id="req-2",
        session_id="sess-2",
        decision=_decision(),
        messages=_messages(),
    )
    req = mapper.to_execution_request(plan, provider="openai", model="gpt-5.4")
    assert req.request_id == "req-2"
    assert req.provider == "openai"


def test_fallback_execution_manager_parse_chain() -> None:
    manager = FallbackExecutionManager()
    targets = manager.parse_chain(["anthropic:claude-sonnet", "invalid"])
    assert len(targets) == 1
    assert targets[0].provider == "anthropic"


def test_retry_policy_evaluator_backoff() -> None:
    evaluator = RetryPolicyEvaluator()
    policy = RetryPolicy(max_retries=3, base_backoff_seconds=0.1, exponential_factor=2.0)
    assert evaluator.backoff_seconds(retry_count=1, policy=policy) == 0.1
    assert evaluator.backoff_seconds(retry_count=2, policy=policy) == 0.2


def test_failure_classifier_categories() -> None:
    classifier = FailureClassifier()
    assert classifier.classify(RuntimeError("timeout exceeded")).failure_type == "timeout_failure"
    assert classifier.classify(RuntimeError("rate limit 429")).failure_type == "rate_limit"
    assert classifier.classify(RuntimeError("unauthorized auth failed")).retryable is False


@pytest.mark.asyncio
async def test_retry_lifecycle_success_after_retry() -> None:
    orchestrator = MockOrchestrator(
        responses=[RuntimeError("transient provider transport error"), _result("req-3", "openai", "gpt-5.4")]
    )
    manager = ExecutionLifecycleManager(orchestrator, retry_policy=RetryPolicy(max_retries=2, base_backoff_seconds=0.0))
    plan = ExecutionPlan(
        request_id="req-3",
        session_id="sess-3",
        primary_provider="openai",
        primary_model="gpt-5.4",
        fallback_chain=[],
        execution_strategy="standard",
        messages=_messages(),
    )
    outcome = await manager.execute(plan)
    assert outcome.snapshot.state == "completed"
    assert outcome.snapshot.retry_count == 1


@pytest.mark.asyncio
async def test_fallback_execution_failover() -> None:
    orchestrator = MockOrchestrator(
        responses=[RuntimeError("provider unavailable"), _result("req-4", "anthropic", "claude-sonnet")]
    )
    manager = ExecutionLifecycleManager(orchestrator, retry_policy=RetryPolicy(max_retries=0, base_backoff_seconds=0.0))
    plan = ExecutionPlan(
        request_id="req-4",
        session_id="sess-4",
        primary_provider="openai",
        primary_model="gpt-5.4",
        fallback_chain=["anthropic:claude-sonnet"],
        execution_strategy="standard",
        messages=_messages(),
    )
    outcome = await manager.execute(plan)
    assert outcome.snapshot.state == "completed"
    assert outcome.snapshot.active_provider == "anthropic"


@pytest.mark.asyncio
async def test_execution_state_failed_when_all_fail() -> None:
    orchestrator = MockOrchestrator(
        responses=[RuntimeError("provider unavailable"), RuntimeError("provider unavailable")]
    )
    manager = ExecutionLifecycleManager(orchestrator, retry_policy=RetryPolicy(max_retries=0, base_backoff_seconds=0.0))
    plan = ExecutionPlan(
        request_id="req-5",
        session_id="sess-5",
        primary_provider="openai",
        primary_model="gpt-5.4",
        fallback_chain=["anthropic:claude-sonnet"],
        execution_strategy="standard",
        messages=_messages(),
    )
    outcome = await manager.execute(plan)
    assert outcome.snapshot.state == "failed"


@pytest.mark.asyncio
async def test_retry_engine_cancellation() -> None:
    retry_engine = RetryEngine()
    policy = RetryPolicy(max_retries=2, base_backoff_seconds=0.0)

    async def op():
        raise RuntimeError("transient provider transport error")

    cancelled = True

    def is_cancelled() -> bool:
        return cancelled

    with pytest.raises(asyncio.CancelledError):
        await retry_engine.run(
            operation=op,
            classify_failure=FailureClassifier().classify,
            policy=policy,
            is_cancelled=is_cancelled,
        )


@pytest.mark.asyncio
async def test_execution_lifecycle_interrupted_on_cancel() -> None:
    orchestrator = MockOrchestrator(responses=[_result("req-6", "openai", "gpt-5.4")])
    manager = ExecutionLifecycleManager(orchestrator, retry_policy=RetryPolicy(max_retries=0, base_backoff_seconds=0.0))
    manager.cancel("req-6")
    plan = ExecutionPlan(
        request_id="req-6",
        session_id="sess-6",
        primary_provider="openai",
        primary_model="gpt-5.4",
        fallback_chain=[],
        execution_strategy="standard",
        messages=_messages(),
    )
    outcome = await manager.execute(plan)
    assert outcome.snapshot.state == "failed"
