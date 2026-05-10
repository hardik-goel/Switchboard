from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

from smart_router.core.interfaces.provider import ProviderAdapter
from smart_router.schemas.provider import ProviderMessage, ProviderResponse


class DummyProvider:
    name = "dummy"

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


def test_provider_protocol_runtime_checkable() -> None:
    provider = DummyProvider()
    assert isinstance(provider, ProviderAdapter)
