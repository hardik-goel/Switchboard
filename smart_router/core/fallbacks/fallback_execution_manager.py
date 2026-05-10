"""Fallback execution manager for provider failover."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from collections.abc import Awaitable, Callable
from typing import Any

from smart_router.core.execution.route_execution_mapper import RouteExecutionMapper
from smart_router.core.execution.schemas import ExecutionPlan
from smart_router.core.orchestrator.schemas import ExecutionRequest
from smart_router.core.persistence import maybe_persist

TelemetryHook = Callable[[dict[str, Any]], Awaitable[None] | None]
PersistenceHook = Callable[[dict[str, Any]], Awaitable[None] | None]


@dataclass(frozen=True)
class FallbackTarget:
    provider: str
    model: str


class FallbackExecutionManager:
    """Manage provider failover chain and request remapping."""

    def __init__(
        self,
        mapper: RouteExecutionMapper | None = None,
        telemetry_hook: TelemetryHook | None = None,
        persistence_hook: PersistenceHook | None = None,
    ) -> None:
        self._mapper = mapper or RouteExecutionMapper()
        self._telemetry_hook = telemetry_hook
        self._persistence_hook = persistence_hook

    def parse_chain(self, chain: list[str]) -> list[FallbackTarget]:
        targets: list[FallbackTarget] = []
        for item in chain:
            if ":" not in item:
                continue
            provider, model = item.split(":", 1)
            if provider and model:
                targets.append(FallbackTarget(provider=provider, model=model))
        return targets

    def build_request(self, *, plan: ExecutionPlan, target: FallbackTarget) -> ExecutionRequest:
        payload = {
            "event_type": "fallback_triggered",
            "request_id": plan.request_id,
            "session_id": plan.session_id,
            "provider": plan.primary_provider,
            "model": plan.primary_model,
            "execution_state": "fallback_active",
            "metadata": {"fallback_provider": target.provider, "fallback_model": target.model},
        }
        self._emit_fallback_event(payload)
        self._emit_fallback_persistence(payload)
        return self._mapper.to_execution_request(plan, provider=target.provider, model=target.model)

    def _emit_fallback_event(self, payload: dict[str, Any]) -> None:
        if self._telemetry_hook is None:
            return
        result = self._telemetry_hook(payload)
        if inspect.isawaitable(result):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(result)
            except RuntimeError:
                return

    def _emit_fallback_persistence(self, payload: dict[str, Any]) -> None:
        if self._persistence_hook is None:
            return
        result = maybe_persist(self._persistence_hook, payload)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(result)
        except RuntimeError:
            return
