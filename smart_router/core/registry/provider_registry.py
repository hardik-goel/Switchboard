"""Provider adapter registry for runtime lookup and construction."""

from __future__ import annotations

import logging
from collections.abc import Callable

from smart_router.core.interfaces.provider import ProviderAdapter

logger = logging.getLogger("smart_router.registry.providers")

ProviderFactory = Callable[[], ProviderAdapter]


class ProviderRegistryError(RuntimeError):
    """Raised on provider registration and lookup errors."""


class ProviderRegistry:
    """Register and instantiate provider adapters by provider name."""

    def __init__(self) -> None:
        self._factories: dict[str, ProviderFactory] = {}

    def register(self, name: str, factory: ProviderFactory) -> None:
        """Register a provider factory by name."""
        normalized = name.strip().lower()
        if not normalized:
            raise ProviderRegistryError("Provider name cannot be empty.")
        if normalized in self._factories:
            raise ProviderRegistryError(f"Provider already registered: {normalized}")

        self._factories[normalized] = factory
        logger.info("provider_registered", extra={"provider": normalized})

    def create(self, name: str) -> ProviderAdapter:
        """Create adapter instance by registered provider name."""
        normalized = name.strip().lower()
        try:
            factory = self._factories[normalized]
        except KeyError as exc:
            raise ProviderRegistryError(f"Unknown provider: {normalized}") from exc

        adapter = factory()
        if adapter.name.strip().lower() != normalized:
            raise ProviderRegistryError(
                "Provider factory returned adapter with mismatched name "
                f"(expected={normalized}, actual={adapter.name})."
            )
        return adapter

    def list_providers(self) -> list[str]:
        """Return sorted provider names currently registered."""
        return sorted(self._factories)
