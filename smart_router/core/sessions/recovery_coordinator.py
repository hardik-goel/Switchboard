"""Recovery coordinator for interrupted execution restoration."""

from __future__ import annotations

from smart_router.core.execution.schemas import ExecutionPlan
from smart_router.core.persistence.session_persistence_engine import SessionPersistenceEngine


class RecoveryCoordinator:
    """Restore interrupted/resumable sessions and reconstruct execution state."""

    def __init__(self, persistence: SessionPersistenceEngine) -> None:
        self._persistence = persistence

    async def recover_plan(self, session_id: str) -> ExecutionPlan | None:
        session = await self._persistence.restore_session(session_id)
        snapshot = await self._persistence.restore_latest_snapshot(session_id)
        if session is None or snapshot is None:
            return None

        payload = snapshot.payload
        plan_payload = payload.get("plan") if isinstance(payload.get("plan"), dict) else None
        if plan_payload:
            return ExecutionPlan.model_validate(plan_payload)

        # Require prior plan snapshot for safe replay.
        return None

    async def mark_resumed(self, session_id: str) -> None:
        session = await self._persistence.restore_session(session_id)
        if session is None:
            return
        session.lifecycle_state = "resumed"
        session.recovery_state = "restored"
        await self._persistence.persist_session(session)
