"""Recoverable context snapshot management."""

from __future__ import annotations

from smart_router.core.persistence.store import SessionStore
from smart_router.core.sessions.schemas import ContextSnapshot


class ContextSnapshotManager:
    """Manage snapshots used for interruption recovery and continuation."""

    def __init__(self, store: SessionStore) -> None:
        self._store = store

    async def create_snapshot(self, snapshot: ContextSnapshot) -> None:
        await self._store.save_snapshot(snapshot)

    async def latest(self, session_id: str) -> ContextSnapshot | None:
        return await self._store.latest_snapshot(session_id)
