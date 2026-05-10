"""Central telemetry ingestion and coordination manager."""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from smart_router.core.analytics.execution_analytics_engine import ExecutionAnalyticsEngine
from smart_router.core.telemetry.schemas import TelemetryEvent
from smart_router.core.telemetry.storage import InMemoryTelemetryStorage, TelemetryStorage

logger = logging.getLogger("smart_router.telemetry.manager")

TelemetryHook = Callable[[dict[str, Any]], Awaitable[None] | None]


class TelemetryManager:
    """Ingest, persist, and analyze telemetry events passively."""

    def __init__(
        self,
        *,
        storage: TelemetryStorage | None = None,
        analytics_engine: ExecutionAnalyticsEngine | None = None,
        session_hook: TelemetryHook | None = None,
    ) -> None:
        self._storage = storage or InMemoryTelemetryStorage()
        self._analytics = analytics_engine or ExecutionAnalyticsEngine()
        self._session_hook = session_hook

    async def record(self, event: TelemetryEvent) -> None:
        await self._storage.write_event(event)
        await maybe_emit(
            self._session_hook,
            {
                "event_type": event.event_type,
                "request_id": event.request_id,
                "session_id": event.session_id,
                "provider": event.provider,
                "model": event.model,
                "retry_count": event.retry_count,
                "fallback_count": event.fallback_count,
                "execution_state": event.execution_state or "execution_running",
                "metadata": {"telemetry_reference": f\"{event.event_type}:{event.request_id or 'na'}\"},
            },
        )
        logger.info(
            "telemetry_event_recorded",
            extra={
                "request_id": event.request_id,
                "session_id": event.session_id,
                "provider": event.provider,
                "model": event.model,
                "latency": event.latency,
                "cost_estimate": event.cost_estimate,
                "retry_count": event.retry_count,
                "fallback_count": event.fallback_count,
                "execution_state": event.execution_state,
            },
        )

    async def record_payload(self, payload: dict[str, Any]) -> None:
        await self.record(TelemetryEvent.model_validate(payload))

    async def events(self) -> list[TelemetryEvent]:
        return await self._storage.read_events()

    async def analytics_summary(self) -> dict[str, object]:
        events = await self.events()
        return self._analytics.summarize(events)

    def hook(self) -> TelemetryHook:
        async def _hook(payload: dict[str, Any]) -> None:
            await self.record_payload(payload)

        return _hook


async def maybe_emit(hook: TelemetryHook | None, payload: dict[str, Any]) -> None:
    if hook is None:
        return
    result = hook(payload)
    if inspect.isawaitable(result):
        await result
