"""Provider interface contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Protocol, runtime_checkable

from smart_router.schemas.provider import ProviderMessage, ProviderResponse


@runtime_checkable
class ProviderAdapter(Protocol):
    """Unified contract every provider adapter must implement."""

    name: str

    async def generate(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        temperature: float = 0.0,
    ) -> ProviderResponse:
        """Return a normalized response for a message sequence."""

    async def stream(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]:
        """Yield normalized response chunks."""

    async def health_check(self) -> bool:
        """Return provider availability signal."""
