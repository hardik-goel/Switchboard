from __future__ import annotations

from pathlib import Path

import pytest

from smart_router.core.execution import ExecutionLifecycleManager, ExecutionPlanner
from smart_router.core.orchestrator.schemas import ExecutionResult
from smart_router.core.persistence import InMemorySessionStore, SQLiteSessionStore, SessionPersistenceEngine
from smart_router.core.retries import RetryPolicy
from smart_router.core.sessions import (
    ContextSnapshot,
    RecoveryCoordinator,
    SessionLifecycleManager,
    SessionManager,
    SessionRecord,
)
from smart_router.schemas.provider import ProviderMessage, ProviderResponse
from smart_router.schemas.routing import RoutingDecision


class _MockOrchestrator:
    def __init__(self, fail_first: bool = False) -> None:
        self._fail_first = fail_first
        self._calls = 0

    async def execute(self, request):
        self._calls += 1
        if self._fail_first and self._calls == 1:
            raise RuntimeError("transient provider transport error")
        return ExecutionResult(
            request_id=request.request_id or "x",
            provider=request.provider,
            model=request.model,
            response=ProviderResponse(content="ok", model=request.model),
            latency_ms=10,
            retry_count=0,
        )

    def cancel(self, request_id: str, *, reason: str = "cancelled") -> None:
        _ = request_id, reason


def _decision() -> RoutingDecision:
    return RoutingDecision(
        selected_provider="openai",
        selected_model="gpt-5.4",
        reasoning_summary="x",
        fallback_chain=["anthropic:claude-sonnet"],
        estimated_cost=0.1,
        estimated_latency=1000,
        routing_confidence=0.8,
        selected_capabilities=["code_editing"],
        execution_strategy="standard",
    )


def _messages() -> list[ProviderMessage]:
    return [ProviderMessage(role="user", content="hello")]


@pytest.mark.asyncio
async def test_session_manager_create_restore() -> None:
    persistence = SessionPersistenceEngine(InMemorySessionStore())
    manager = SessionManager(persistence)
    await manager.create_session(session_id="s1", request_id="r1")
    restored = await manager.restore_session("s1")
    assert restored is not None
    assert restored.lifecycle_state == "session_created"


@pytest.mark.asyncio
async def test_session_lifecycle_transition() -> None:
    persistence = SessionPersistenceEngine(InMemorySessionStore())
    sm = SessionManager(persistence)
    record = await sm.create_session(session_id="s2", request_id="r2")
    lifecycle = SessionLifecycleManager(persistence)
    updated = await lifecycle.transition(record, new_state="execution_running")
    assert updated.lifecycle_state == "execution_running"


@pytest.mark.asyncio
async def test_snapshot_and_recovery_restore_plan() -> None:
    persistence = SessionPersistenceEngine(InMemorySessionStore())
    plan = ExecutionPlanner().create_plan(
        request_id="r3",
        session_id="s3",
        decision=_decision(),
        messages=_messages(),
    )
    await persistence.persist_snapshot(
        ContextSnapshot(session_id="s3", request_id="r3", snapshot_type="plan", payload={"plan": plan.model_dump()})
    )
    await persistence.persist_session(
        SessionRecord(
            session_id="s3",
            request_id="r3",
            lifecycle_state="resumable",
            provider="openai",
            model="gpt-5.4",
        )
    )
    recovered = await RecoveryCoordinator(persistence).recover_plan("s3")
    assert recovered is not None
    assert recovered.primary_provider == "openai"


@pytest.mark.asyncio
async def test_sqlite_session_store_persistence(tmp_path: Path) -> None:
    persistence = SessionPersistenceEngine(SQLiteSessionStore(tmp_path / "sessions.db"))
    manager = SessionManager(persistence)
    await manager.create_session(session_id="s4", request_id="r4")
    restored = await manager.restore_session("s4")
    assert restored is not None


@pytest.mark.asyncio
async def test_execution_lifecycle_persistence_hooks_retry_continuity() -> None:
    store = InMemorySessionStore()
    persistence = SessionPersistenceEngine(store)
    lifecycle = ExecutionLifecycleManager(
        _MockOrchestrator(fail_first=True),
        retry_policy=RetryPolicy(max_retries=2, base_backoff_seconds=0.0),
        persistence_hook=persistence.hook(),
    )

    plan = ExecutionPlanner().create_plan(
        request_id="r5",
        session_id="s5",
        decision=_decision(),
        messages=_messages(),
    )
    outcome = await lifecycle.execute(plan)
    assert outcome.snapshot.state == "completed"

    session = await persistence.restore_session("s5")
    assert session is not None
    transitions = await persistence.restore_transitions("s5")
    assert transitions


@pytest.mark.asyncio
async def test_fallback_continuity_persistence() -> None:
    class FailingFirstProvider(_MockOrchestrator):
        async def execute(self, request):
            self._calls += 1
            if self._calls == 1:
                raise RuntimeError("provider unavailable")
            return ExecutionResult(
                request_id=request.request_id or "x",
                provider=request.provider,
                model=request.model,
                response=ProviderResponse(content="ok", model=request.model),
                latency_ms=12,
                retry_count=0,
            )

    persistence = SessionPersistenceEngine(InMemorySessionStore())
    lifecycle = ExecutionLifecycleManager(
        FailingFirstProvider(),
        retry_policy=RetryPolicy(max_retries=0, base_backoff_seconds=0.0),
        persistence_hook=persistence.hook(),
    )

    plan = ExecutionPlanner().create_plan(
        request_id="r6",
        session_id="s6",
        decision=_decision(),
        messages=_messages(),
    )
    outcome = await lifecycle.execute(plan)
    assert outcome.snapshot.state == "completed"
    assert outcome.snapshot.fallback_provider == "anthropic"


@pytest.mark.asyncio
async def test_restart_restoration_latest_snapshot() -> None:
    persistence = SessionPersistenceEngine(InMemorySessionStore())
    await persistence.persist_snapshot(
        ContextSnapshot(
            session_id="s7",
            request_id="r7",
            snapshot_type="lifecycle_checkpoint",
            payload={"execution_state": "interrupted"},
        )
    )
    latest = await persistence.restore_latest_snapshot("s7")
    assert latest is not None
    assert latest.payload["execution_state"] == "interrupted"
