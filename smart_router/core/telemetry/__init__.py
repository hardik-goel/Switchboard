"""Telemetry and observability package."""

from smart_router.core.telemetry.manager import TelemetryManager, maybe_emit
from smart_router.core.telemetry.schemas import TelemetryEvent, TelemetryEventType
from smart_router.core.telemetry.storage import InMemoryTelemetryStorage, SQLiteTelemetryStorage, TelemetryStorage

__all__ = [
    "TelemetryManager",
    "TelemetryEvent",
    "TelemetryEventType",
    "TelemetryStorage",
    "InMemoryTelemetryStorage",
    "SQLiteTelemetryStorage",
    "maybe_emit",
]
