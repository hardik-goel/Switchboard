"""Routing engine interface contract."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from smart_router.schemas.classification import PromptClassification
from smart_router.schemas.prompt import PromptRequest
from smart_router.schemas.routing import RoutingDecision


@runtime_checkable
class RoutingEngine(Protocol):
    """Contract for deterministic routing decisions."""

    async def choose_route(
        self,
        request: PromptRequest,
        classification: PromptClassification,
    ) -> RoutingDecision:
        """Choose provider/model using config + policy + telemetry."""
