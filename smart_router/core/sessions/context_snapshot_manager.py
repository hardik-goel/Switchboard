"""Session-level snapshot helper wrapper."""

from __future__ import annotations

from smart_router.core.persistence.session_persistence_engine import SessionPersistenceEngine
from smart_router.core.sessions.schemas import ContextSnapshot


class ContextSnapshotManager:
    """Create session-oriented snapshots for partial continuation."""

    def __init__(self, persistence: SessionPersistenceEngine) -> None:
        self._persistence = persistence

    async def checkpoint(self, snapshot: ContextSnapshot) -> None:
        await self._persistence.persist_snapshot(snapshot)

    async def latest(self, session_id: str) -> ContextSnapshot | None:
        return await self._persistence.restore_latest_snapshot(session_id)
