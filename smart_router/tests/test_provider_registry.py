from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import pytest

from smart_router.core.registry import ProviderRegistry, ProviderRegistryError
from smart_router.schemas.provider import ProviderMessage, ProviderResponse


class DummyProvider:
    name = "openai"

    async def generate(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        temperature: float = 0.0,
    ) -> ProviderResponse:
        _ = messages, temperature
        return ProviderResponse(content="ok", model=model)

    async def stream(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]:
        _ = messages, model, temperature
        if False:
            yield ""

    async def health_check(self) -> bool:
        return True


def test_registry_register_and_create() -> None:
    registry = ProviderRegistry()
    registry.register("openai", lambda: DummyProvider())
    created = registry.create("openai")
    assert created.name == "openai"


def test_registry_duplicate_registration_fails() -> None:
    registry = ProviderRegistry()
    registry.register("openai", lambda: DummyProvider())
    with pytest.raises(ProviderRegistryError):
        registry.register("openai", lambda: DummyProvider())
