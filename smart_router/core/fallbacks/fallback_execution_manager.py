"""Fallback execution manager for provider failover."""

from __future__ import annotations

from dataclasses import dataclass

from smart_router.core.execution.route_execution_mapper import RouteExecutionMapper
from smart_router.core.execution.schemas import ExecutionPlan
from smart_router.core.orchestrator.schemas import ExecutionRequest


@dataclass(frozen=True)
class FallbackTarget:
    provider: str
    model: str


class FallbackExecutionManager:
    """Manage provider failover chain and request remapping."""

    def __init__(self, mapper: RouteExecutionMapper | None = None) -> None:
        self._mapper = mapper or RouteExecutionMapper()

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
        return self._mapper.to_execution_request(plan, provider=target.provider, model=target.model)
