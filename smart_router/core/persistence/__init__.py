"""Persistence abstraction package."""

from smart_router.core.persistence.session_persistence_engine import SessionPersistenceEngine, maybe_persist
from smart_router.core.persistence.store import InMemorySessionStore, SQLiteSessionStore, SessionStore

__all__ = [
    "SessionStore",
    "InMemorySessionStore",
    "SQLiteSessionStore",
    "SessionPersistenceEngine",
    "maybe_persist",
]
