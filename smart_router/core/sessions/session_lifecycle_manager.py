"""Session lifecycle transition manager."""

from __future__ import annotations

import logging

from smart_router.core.persistence.session_persistence_engine import SessionPersistenceEngine
from smart_router.core.sessions.schemas import SessionRecord, StateTransitionRecord

logger = logging.getLogger("smart_router.sessions.lifecycle")


class SessionLifecycleManager:
    """Manage session lifecycle state transitions."""

    def __init__(self, persistence: SessionPersistenceEngine) -> None:
        self._persistence = persistence

    async def transition(self, record: SessionRecord, *, new_state: str, metadata: dict[str, object] | None = None) -> SessionRecord:
        record.lifecycle_state = new_state
        if metadata:
            record.metadata.update(metadata)
        await self._persistence.persist_session(record)
        await self._persistence.persist_transition(
            StateTransitionRecord(
                session_id=record.session_id,
                request_id=record.request_id,
                lifecycle_state=new_state,
                provider=record.provider,
                model=record.model,
                retry_count=record.retry_count,
                fallback_count=record.fallback_count,
                recovery_state=record.recovery_state,
                metadata=metadata or {},
            )
        )
        logger.info(
            "session_transition",
            extra={
                "request_id": record.request_id,
                "session_id": record.session_id,
                "lifecycle_state": record.lifecycle_state,
                "provider": record.provider,
                "model": record.model,
                "recovery_state": record.recovery_state,
                "retry_count": record.retry_count,
                "fallback_count": record.fallback_count,
            },
        )
        return record
