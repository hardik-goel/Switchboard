"""Session manager for creation/restoration and metadata updates."""

from __future__ import annotations

import logging

from smart_router.core.persistence.session_persistence_engine import SessionPersistenceEngine
from smart_router.core.sessions.schemas import SessionRecord

logger = logging.getLogger("smart_router.sessions.manager")


class SessionManager:
    """Create/manage persistent execution sessions."""

    def __init__(self, persistence: SessionPersistenceEngine) -> None:
        self._persistence = persistence

    async def create_session(self, *, session_id: str, request_id: str) -> SessionRecord:
        record = SessionRecord(session_id=session_id, request_id=request_id, lifecycle_state="session_created")
        await self._persistence.persist_session(record)
        logger.info(
            "session_created",
            extra={
                "request_id": request_id,
                "session_id": session_id,
                "lifecycle_state": record.lifecycle_state,
                "provider": record.provider,
                "model": record.model,
                "recovery_state": record.recovery_state,
                "retry_count": record.retry_count,
                "fallback_count": record.fallback_count,
            },
        )
        return record

    async def restore_session(self, session_id: str) -> SessionRecord | None:
        return await self._persistence.restore_session(session_id)

    async def update_session(self, record: SessionRecord) -> None:
        await self._persistence.persist_session(record)
