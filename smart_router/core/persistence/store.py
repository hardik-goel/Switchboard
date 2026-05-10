"""Session persistence abstraction and SQLite backend."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Protocol

from smart_router.core.sessions.schemas import ContextSnapshot, SessionRecord, StateTransitionRecord


class SessionStore(Protocol):
    """Abstract persistence backend for sessions and transitions."""

    async def upsert_session(self, record: SessionRecord) -> None:
        ...

    async def get_session(self, session_id: str) -> SessionRecord | None:
        ...

    async def append_transition(self, record: StateTransitionRecord) -> None:
        ...

    async def list_transitions(self, session_id: str) -> list[StateTransitionRecord]:
        ...

    async def save_snapshot(self, snapshot: ContextSnapshot) -> None:
        ...

    async def latest_snapshot(self, session_id: str) -> ContextSnapshot | None:
        ...


class InMemorySessionStore:
    """In-memory session store backend."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._transitions: dict[str, list[StateTransitionRecord]] = {}
        self._snapshots: dict[str, list[ContextSnapshot]] = {}

    async def upsert_session(self, record: SessionRecord) -> None:
        self._sessions[record.session_id] = record

    async def get_session(self, session_id: str) -> SessionRecord | None:
        return self._sessions.get(session_id)

    async def append_transition(self, record: StateTransitionRecord) -> None:
        self._transitions.setdefault(record.session_id, []).append(record)

    async def list_transitions(self, session_id: str) -> list[StateTransitionRecord]:
        return list(self._transitions.get(session_id, []))

    async def save_snapshot(self, snapshot: ContextSnapshot) -> None:
        self._snapshots.setdefault(snapshot.session_id, []).append(snapshot)

    async def latest_snapshot(self, session_id: str) -> ContextSnapshot | None:
        snapshots = self._snapshots.get(session_id, [])
        return snapshots[-1] if snapshots else None


class SQLiteSessionStore:
    """SQLite session store backend."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    lifecycle_state TEXT NOT NULL,
                    provider TEXT,
                    model TEXT,
                    retry_count INTEGER NOT NULL,
                    fallback_count INTEGER NOT NULL,
                    recovery_state TEXT,
                    telemetry_refs_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS state_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    lifecycle_state TEXT NOT NULL,
                    provider TEXT,
                    model TEXT,
                    retry_count INTEGER NOT NULL,
                    fallback_count INTEGER NOT NULL,
                    recovery_state TEXT,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS context_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    snapshot_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    async def upsert_session(self, record: SessionRecord) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO sessions (
                    session_id, request_id, lifecycle_state, provider, model,
                    retry_count, fallback_count, recovery_state, telemetry_refs_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    request_id=excluded.request_id,
                    lifecycle_state=excluded.lifecycle_state,
                    provider=excluded.provider,
                    model=excluded.model,
                    retry_count=excluded.retry_count,
                    fallback_count=excluded.fallback_count,
                    recovery_state=excluded.recovery_state,
                    telemetry_refs_json=excluded.telemetry_refs_json,
                    metadata_json=excluded.metadata_json
                """,
                (
                    record.session_id,
                    record.request_id,
                    record.lifecycle_state,
                    record.provider,
                    record.model,
                    record.retry_count,
                    record.fallback_count,
                    record.recovery_state,
                    json.dumps(record.telemetry_references),
                    json.dumps(record.metadata),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    async def get_session(self, session_id: str) -> SessionRecord | None:
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                """
                SELECT request_id, lifecycle_state, provider, model, retry_count,
                       fallback_count, recovery_state, telemetry_refs_json, metadata_json
                FROM sessions WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return SessionRecord(
            session_id=session_id,
            request_id=row[0],
            lifecycle_state=row[1],
            provider=row[2],
            model=row[3],
            retry_count=int(row[4]),
            fallback_count=int(row[5]),
            recovery_state=row[6],
            telemetry_references=json.loads(row[7]),
            metadata=json.loads(row[8]),
        )

    async def append_transition(self, record: StateTransitionRecord) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO state_transitions (
                    session_id, request_id, lifecycle_state, provider, model,
                    retry_count, fallback_count, recovery_state, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.session_id,
                    record.request_id,
                    record.lifecycle_state,
                    record.provider,
                    record.model,
                    record.retry_count,
                    record.fallback_count,
                    record.recovery_state,
                    json.dumps(record.metadata),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    async def list_transitions(self, session_id: str) -> list[StateTransitionRecord]:
        conn = sqlite3.connect(self._db_path)
        try:
            rows = conn.execute(
                """
                SELECT request_id, lifecycle_state, provider, model, retry_count,
                       fallback_count, recovery_state, metadata_json
                FROM state_transitions WHERE session_id = ? ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        finally:
            conn.close()
        return [
            StateTransitionRecord(
                session_id=session_id,
                request_id=row[0],
                lifecycle_state=row[1],
                provider=row[2],
                model=row[3],
                retry_count=int(row[4]),
                fallback_count=int(row[5]),
                recovery_state=row[6],
                metadata=json.loads(row[7]),
            )
            for row in rows
        ]

    async def save_snapshot(self, snapshot: ContextSnapshot) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO context_snapshots (session_id, request_id, snapshot_type, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    snapshot.session_id,
                    snapshot.request_id,
                    snapshot.snapshot_type,
                    json.dumps(snapshot.payload),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    async def latest_snapshot(self, session_id: str) -> ContextSnapshot | None:
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                """
                SELECT request_id, snapshot_type, payload_json
                FROM context_snapshots WHERE session_id = ? ORDER BY id DESC LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return ContextSnapshot(
            session_id=session_id,
            request_id=row[0],
            snapshot_type=row[1],
            payload=json.loads(row[2]),
        )
