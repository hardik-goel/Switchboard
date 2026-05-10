"""Session persistence engine coordinating state/snapshot/session writes."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from smart_router.core.persistence.store import SessionStore
from smart_router.core.sessions.schemas import ContextSnapshot, SessionRecord, StateTransitionRecord
from smart_router.core.state.context_snapshot_manager import ContextSnapshotManager
from smart_router.core.state.execution_state_store import ExecutionStateStore
from smart_router.schemas.routing import RoutingDecision

PersistenceHook = Callable[[dict[str, Any]], Awaitable[None] | None]


class SessionPersistenceEngine:
    """Persist lifecycle and context data without owning execution logic."""

    def __init__(self, store: SessionStore) -> None:
        self._store = store
        self._state_store = ExecutionStateStore(store)
        self._snapshot_manager = ContextSnapshotManager(store)

    async def persist_session(self, record: SessionRecord) -> None:
        await self._store.upsert_session(record)

    async def persist_transition(self, record: StateTransitionRecord) -> None:
        await self._state_store.append(record)

    async def persist_snapshot(self, snapshot: ContextSnapshot) -> None:
        await self._snapshot_manager.create_snapshot(snapshot)

    async def restore_session(self, session_id: str) -> SessionRecord | None:
        return await self._store.get_session(session_id)

    async def restore_transitions(self, session_id: str) -> list[StateTransitionRecord]:
        return await self._state_store.list(session_id)

    async def restore_latest_snapshot(self, session_id: str) -> ContextSnapshot | None:
        return await self._snapshot_manager.latest(session_id)

    async def persist_routing_decision(self, *, session_id: str, request_id: str, decision: RoutingDecision) -> None:
        await self.persist_snapshot(
            ContextSnapshot(
                session_id=session_id,
                request_id=request_id,
                snapshot_type="routing_decision",
                payload={"routing_decision": decision.model_dump()},
            )
        )

    async def persist_execution_plan(self, *, session_id: str, request_id: str, plan_payload: dict[str, Any]) -> None:
        await self.persist_snapshot(
            ContextSnapshot(
                session_id=session_id,
                request_id=request_id,
                snapshot_type="execution_plan",
                payload={"plan": plan_payload},
            )
        )

    def hook(self) -> PersistenceHook:
        async def _hook(payload: dict[str, Any]) -> None:
            await self._persist_from_payload(payload)

        return _hook

    async def _persist_from_payload(self, payload: dict[str, Any]) -> None:
        session_id = payload.get("session_id")
        request_id = payload.get("request_id")
        if not session_id or not request_id:
            return
        state = payload.get("execution_state") or "execution_running"
        provider = payload.get("provider")
        model = payload.get("model")
        retry_count = int(payload.get("retry_count", 0))
        fallback_count = int(payload.get("fallback_count", 0))
        metadata = payload.get("metadata") or {}
        existing = await self.restore_session(session_id)
        telemetry_refs = list(existing.telemetry_references) if existing else []
        telemetry_ref = metadata.get("telemetry_reference") if isinstance(metadata, dict) else None
        if isinstance(telemetry_ref, str):
            telemetry_refs.append(telemetry_ref)
        recovery_state = None
        if state in ("interrupted", "failed"):
            recovery_state = "resumable"
        if state in ("resumed", "completed"):
            recovery_state = "restored"

        await self.persist_session(
            SessionRecord(
                session_id=session_id,
                request_id=request_id,
                lifecycle_state=state,
                provider=provider,
                model=model,
                retry_count=retry_count,
                fallback_count=fallback_count,
                recovery_state=recovery_state,
                telemetry_references=telemetry_refs,
                metadata=metadata if isinstance(metadata, dict) else {},
            )
        )
        await self.persist_transition(
            StateTransitionRecord(
                session_id=session_id,
                request_id=request_id,
                lifecycle_state=state,
                provider=provider,
                model=model,
                retry_count=retry_count,
                fallback_count=fallback_count,
                metadata=metadata if isinstance(metadata, dict) else {},
            )
        )
        await self.persist_snapshot(
            ContextSnapshot(
                session_id=session_id,
                request_id=request_id,
                snapshot_type="lifecycle_checkpoint",
                payload=payload,
            )
        )


async def maybe_persist(hook: PersistenceHook | None, payload: dict[str, Any]) -> None:
    if hook is None:
        return
    result = hook(payload)
    if inspect.isawaitable(result):
        await result
