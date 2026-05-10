from __future__ import annotations

from pathlib import Path

import pytest

from smart_router.core.analytics import ExecutionAnalyticsEngine, HealthMetricsAggregator, ProviderPerformanceTracker
from smart_router.core.execution import ExecutionLifecycleManager, ExecutionPlanner
from smart_router.core.orchestrator.schemas import ExecutionResult
from smart_router.core.router import RoutingEngine, RouterRuntimeContext
from smart_router.core.telemetry import InMemoryTelemetryStorage, SQLiteTelemetryStorage, TelemetryEvent, TelemetryManager
from smart_router.core.config import ConfigEngine
from smart_router.schemas.classification import PromptClassification
from smart_router.schemas.prompt import PromptRequest
from smart_router.schemas.provider import ProviderMessage, ProviderResponse
from smart_router.schemas.routing import RoutingDecision


@pytest.mark.asyncio
async def test_telemetry_ingestion_and_readback() -> None:
    manager = TelemetryManager(storage=InMemoryTelemetryStorage())
    await manager.record(
        TelemetryEvent(
            event_type="execution_started",
            request_id="r1",
            provider="openai",
            model="gpt-5.4",
            execution_state="running",
        )
    )
    events = await manager.events()
    assert len(events) == 1
    assert events[0].event_type == "execution_started"


@pytest.mark.asyncio
async def test_sqlite_persistence_abstraction(tmp_path: Path) -> None:
    storage = SQLiteTelemetryStorage(tmp_path / "telemetry.db")
    manager = TelemetryManager(storage=storage)
    await manager.record(TelemetryEvent(event_type="execution_failed", request_id="r2", execution_state="failed"))
    events = await manager.events()
    assert len(events) == 1
    assert events[0].request_id == "r2"


def test_metrics_aggregation_and_health_detection() -> None:
    events = [
        TelemetryEvent(event_type="execution_completed", provider="openai", latency=100.0),
        TelemetryEvent(event_type="execution_failed", provider="openai", latency=200.0),
        TelemetryEvent(event_type="execution_completed", provider="anthropic", latency=120.0),
        TelemetryEvent(event_type="fallback_triggered", provider="openai"),
        TelemetryEvent(event_type="route_selected", provider="openai", model="gpt-5.4", metadata={"routing_confidence": 0.8}),
    ]
    analytics = ExecutionAnalyticsEngine().summarize(events)
    assert analytics["event_counts"]["execution_completed"] == 2
    assert "openai" in analytics["provider_health_scores"]
    assert isinstance(analytics["degraded_providers"], list)


def test_provider_performance_tracker() -> None:
    tracker = ProviderPerformanceTracker()
    rates = tracker.success_failure_rates(
        [
            TelemetryEvent(event_type="execution_completed", provider="openai"),
            TelemetryEvent(event_type="execution_failed", provider="openai"),
        ]
    )
    assert rates["openai"]["success_rate"] == 0.5


def test_health_metrics_aggregator_degradation() -> None:
    agg = HealthMetricsAggregator()
    degraded = agg.degraded_providers(
        [
            TelemetryEvent(event_type="execution_failed", provider="openai"),
            TelemetryEvent(event_type="execution_failed", provider="openai"),
        ],
        threshold=0.6,
    )
    assert "openai" in degraded


@pytest.mark.asyncio
async def test_routing_engine_telemetry_hook() -> None:
    manager = TelemetryManager(storage=InMemoryTelemetryStorage())
    config = ConfigEngine(Path("smart_router/configs/default.yaml")).load()
    router = RoutingEngine(config, telemetry_hook=manager.hook())

    classification = PromptClassification(
        complexity_level="low",
        complexity_score=0.2,
        reasoning_depth="low",
        estimated_input_tokens=20,
        estimated_output_tokens=100,
        estimated_total_tokens=120,
        context_expansion_tokens=0,
        repo_scope="single_file",
        latency_sensitivity="low",
        task_type="bugfix",
        confidence_score=0.8,
        suggested_capabilities=["code_editing"],
        execution_risk_level="low",
    )

    await router.choose_route(
        PromptRequest(prompt="fix typo", session_id="s1"),
        classification,
        runtime_context=RouterRuntimeContext(request_id="r-router", session_id="s1"),
    )
    events = await manager.events()
    assert any(e.event_type == "route_selected" for e in events)


class _MockOrchestrator:
    async def execute(self, request):
        return ExecutionResult(
            request_id=request.request_id or "r-x",
            provider=request.provider,
            model=request.model,
            response=ProviderResponse(content="ok", model=request.model),
            latency_ms=50,
            retry_count=0,
        )

    def cancel(self, request_id: str, *, reason: str = "cancelled") -> None:
        _ = request_id, reason


@pytest.mark.asyncio
async def test_execution_lifecycle_telemetry_hook() -> None:
    manager = TelemetryManager(storage=InMemoryTelemetryStorage())
    lifecycle = ExecutionLifecycleManager(_MockOrchestrator(), telemetry_hook=manager.hook())
    decision = RoutingDecision(
        selected_provider="openai",
        selected_model="gpt-5.4",
        reasoning_summary="x",
        fallback_chain=[],
        estimated_cost=0.1,
        estimated_latency=1000,
        routing_confidence=0.9,
        selected_capabilities=["code_editing"],
        execution_strategy="standard",
    )
    plan = ExecutionPlanner().create_plan(
        request_id="r-lifecycle",
        session_id="s2",
        decision=decision,
        messages=[ProviderMessage(role="user", content="hello")],
    )
    outcome = await lifecycle.execute(plan)
    assert outcome.snapshot.state == "completed"
    events = await manager.events()
    event_types = [e.event_type for e in events]
    assert "execution_started" in event_types
    assert "execution_completed" in event_types
