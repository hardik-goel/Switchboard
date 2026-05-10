"""Execution state transition persistence."""

from __future__ import annotations

from smart_router.core.persistence.store import SessionStore
from smart_router.core.sessions.schemas import StateTransitionRecord


class ExecutionStateStore:
    """Persist and retrieve normalized execution state transitions."""

    def __init__(self, store: SessionStore) -> None:
        self._store = store

    async def append(self, record: StateTransitionRecord) -> None:
        await self._store.append_transition(record)

    async def list(self, session_id: str) -> list[StateTransitionRecord]:
        return await self._store.list_transitions(session_id)
