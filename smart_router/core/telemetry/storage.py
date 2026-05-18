"""Telemetry persistence abstraction and SQLite backend."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Protocol

from smart_router.core.telemetry.schemas import TelemetryEvent


class TelemetryStorage(Protocol):
    """Persistence backend contract for telemetry events."""

    async def write_event(self, event: TelemetryEvent) -> None:
        ...

    async def read_events(self) -> list[TelemetryEvent]:
        ...


class InMemoryTelemetryStorage:
    """In-memory storage backend for testing and local development."""

    def __init__(self) -> None:
        self._events: list[TelemetryEvent] = []

    async def write_event(self, event: TelemetryEvent) -> None:
        self._events.append(event)

    async def read_events(self) -> list[TelemetryEvent]:
        return list(self._events)


class SQLiteTelemetryStorage:
    """SQLite telemetry backend with append-only event table."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    request_id TEXT,
                    session_id TEXT,
                    provider TEXT,
                    model TEXT,
                    latency REAL,
                    cost_estimate REAL,
                    retry_count INTEGER NOT NULL,
                    fallback_count INTEGER NOT NULL,
                    execution_state TEXT,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    async def write_event(self, event: TelemetryEvent) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO telemetry_events (
                    event_type, request_id, session_id, provider, model, latency,
                    cost_estimate, retry_count, fallback_count, execution_state, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_type,
                    event.request_id,
                    event.session_id,
                    event.provider,
                    event.model,
                    event.latency,
                    event.cost_estimate,
                    event.retry_count,
                    event.fallback_count,
                    event.execution_state,
                    json.dumps(event.metadata),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    async def read_events(self) -> list[TelemetryEvent]:
        conn = sqlite3.connect(self._db_path)
        try:
            rows = conn.execute(
                """
                SELECT event_type, request_id, session_id, provider, model, latency,
                       cost_estimate, retry_count, fallback_count, execution_state, metadata_json
                FROM telemetry_events
                ORDER BY id ASC
                """
            ).fetchall()
        finally:
            conn.close()

        events: list[TelemetryEvent] = []
        for row in rows:
            events.append(
                TelemetryEvent(
                    event_type=row[0],
                    request_id=row[1],
                    session_id=row[2],
                    provider=row[3],
                    model=row[4],
                    latency=row[5],
                    cost_estimate=row[6],
                    retry_count=int(row[7]),
                    fallback_count=int(row[8]),
                    execution_state=row[9],
                    metadata=json.loads(row[10]),
                )
            )
        return events
