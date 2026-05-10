from __future__ import annotations

import asyncio
import json

import pytest

from smart_router.core.orchestrator import (
    ExecutionFailureError,
    ExecutionRequest,
    ProviderOrchestrator,
    ProviderUnavailableError,
)
from smart_router.core.registry import ProviderRegistry
from smart_router.schemas.provider import ProviderMessage, ProviderResponse


class DummyProvider:
    name = "dummy"

    def __init__(self) -> None:
        self._calls = 0

    async def generate(self, messages, *, model: str, temperature: float = 0.0) -> ProviderResponse:
        _ = messages, temperature
        return ProviderResponse(content="ok", model=model, usage={"total_tokens": 2})

    async def stream(self, messages, *, model: str, temperature: float = 0.0):
        _ = messages, temperature
        yield json.dumps({"content_delta": "a", "done": False})
        yield json.dumps({"content_delta": "b", "done": False})
        yield json.dumps({"done": True})

    async def health_check(self) -> bool:
        return True


class FlakyProvider(DummyProvider):
    def __init__(self) -> None:
        super().__init__()

    async def generate(self, messages, *, model: str, temperature: float = 0.0) -> ProviderResponse:
        _ = messages, temperature
        self._calls += 1
        if self._calls == 1:
            raise RuntimeError("transient")
        return ProviderResponse(content="recovered", model=model)


class SlowProvider(DummyProvider):
    async def generate(self, messages, *, model: str, temperature: float = 0.0) -> ProviderResponse:
        _ = messages, temperature
        await asyncio.sleep(0.2)
        return ProviderResponse(content="late", model=model)


class SlowStreamProvider(DummyProvider):
    async def stream(self, messages, *, model: str, temperature: float = 0.0):
        _ = messages, model, temperature
        await asyncio.sleep(0.2)
        yield json.dumps({"content_delta": "x", "done": False})


@pytest.mark.asyncio
async def test_orchestrator_execute_success() -> None:
    registry = ProviderRegistry()
    registry.register("dummy", lambda: DummyProvider())
    orchestrator = ProviderOrchestrator(registry)

    result = await orchestrator.execute(
        ExecutionRequest(
            provider="dummy",
            model="m1",
            messages=[ProviderMessage(role="user", content="hello")],
            session_id="sess-1",
        )
    )

    assert result.provider == "dummy"
    assert result.response.content == "ok"


@pytest.mark.asyncio
async def test_orchestrator_registry_resolution_failure() -> None:
    orchestrator = ProviderOrchestrator(ProviderRegistry())
    with pytest.raises(ProviderUnavailableError):
        await orchestrator.execute(
            ExecutionRequest(
                provider="missing",
                model="m1",
                messages=[ProviderMessage(role="user", content="hello")],
            )
        )


@pytest.mark.asyncio
async def test_orchestrator_retry_safe_execution() -> None:
    registry = ProviderRegistry()
    registry.register("dummy", lambda: FlakyProvider())
    orchestrator = ProviderOrchestrator(registry, max_retries=1)

    result = await orchestrator.execute(
        ExecutionRequest(
            provider="dummy",
            model="m1",
            messages=[ProviderMessage(role="user", content="hello")],
        )
    )
    assert result.response.content == "recovered"
    assert result.retry_count == 1


@pytest.mark.asyncio
async def test_orchestrator_timeout_handling() -> None:
    registry = ProviderRegistry()
    registry.register("dummy", lambda: SlowProvider())
    orchestrator = ProviderOrchestrator(registry, max_retries=0)

    with pytest.raises(ExecutionFailureError):
        await orchestrator.execute(
            ExecutionRequest(
                provider="dummy",
                model="m1",
                messages=[ProviderMessage(role="user", content="hello")],
                timeout_seconds=0.01,
            )
        )


@pytest.mark.asyncio
async def test_stream_normalization_lifecycle() -> None:
    registry = ProviderRegistry()
    registry.register("dummy", lambda: DummyProvider())
    orchestrator = ProviderOrchestrator(registry)

    events = []
    async for event in orchestrator.stream_execute(
        ExecutionRequest(
            provider="dummy",
            model="m1",
            messages=[ProviderMessage(role="user", content="hello")],
            stream=True,
        )
    ):
        events.append(event.event_type)

    assert events == ["stream_started", "token_chunk", "token_chunk", "stream_completed"]


@pytest.mark.asyncio
async def test_stream_timeout_propagation() -> None:
    registry = ProviderRegistry()
    registry.register("dummy", lambda: SlowStreamProvider())
    orchestrator = ProviderOrchestrator(registry)

    events = []
    async for event in orchestrator.stream_execute(
        ExecutionRequest(
            provider="dummy",
            model="m1",
            messages=[ProviderMessage(role="user", content="hello")],
            stream=True,
            timeout_seconds=0.01,
        )
    ):
        events.append(event.event_type)

    assert events == ["stream_started", "stream_interrupted"]


@pytest.mark.asyncio
async def test_stream_cancellation_and_interruption_recovery() -> None:
    registry = ProviderRegistry()
    registry.register("dummy", lambda: DummyProvider())
    orchestrator = ProviderOrchestrator(registry)

    req = ExecutionRequest(
        request_id="req-cancel-1",
        provider="dummy",
        model="m1",
        messages=[ProviderMessage(role="user", content="hello")],
        stream=True,
    )

    events = []
    async for event in orchestrator.stream_execute(req):
        events.append(event.event_type)
        if event.event_type == "stream_started":
            orchestrator.cancel("req-cancel-1", reason="user_interrupt")

    assert events == ["stream_started", "stream_interrupted"]
