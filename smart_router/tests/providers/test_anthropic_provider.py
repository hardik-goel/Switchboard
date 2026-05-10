from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from smart_router.core.config import ConfigEngine
from smart_router.core.interfaces.provider import ProviderAdapter
from smart_router.core.orchestrator import ExecutionRequest, ProviderOrchestrator
from smart_router.core.registry import ProviderRegistry
from smart_router.providers.anthropic import (
    AnthropicAuthError,
    AnthropicMalformedResponseError,
    AnthropicModelUnavailableError,
    AnthropicProvider,
    AnthropicRateLimitError,
    AnthropicTimeoutError,
    AnthropicTransientError,
    register_anthropic_provider,
)
from smart_router.schemas.provider import ProviderMessage


@pytest.fixture
def loaded_engine(monkeypatch: pytest.MonkeyPatch) -> ConfigEngine:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    engine = ConfigEngine(Path("smart_router/configs/default.yaml"))
    engine.load()
    return engine


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_anthropic_generate_normalization(loaded_engine: ConfigEngine) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/messages")
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "hello"}],
                "usage": {"input_tokens": 4, "output_tokens": 6},
            },
        )

    provider = AnthropicProvider.from_config_engine(loaded_engine, client=_client(handler), session_id="s1")
    result = await provider.generate(
        [ProviderMessage(role="user", content="hi")],
        model="claude-sonnet",
    )

    assert result.content == "hello"
    assert result.usage["total_tokens"] == 10


@pytest.mark.asyncio
async def test_anthropic_stream_normalization(loaded_engine: ConfigEngine) -> None:
    class BytesStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"event: message_start\n"
            yield b'data: {"type":"content_block_delta","delta":{"text":"hel"}}\n\n'
            yield b'data: {"type":"content_block_delta","delta":{"text":"lo"}}\n\n'
            yield b'data: {"type":"message_stop"}\n\n'

        async def aclose(self) -> None:
            return None

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=BytesStream())

    provider = AnthropicProvider.from_config_engine(loaded_engine, client=_client(handler))
    events = []
    async for raw in provider.stream([ProviderMessage(role="user", content="hi")], model="claude-sonnet"):
        events.append(json.loads(raw))

    assert events[0]["content_delta"] == "hel"
    assert events[1]["content_delta"] == "lo"
    assert events[-1]["done"] is True


@pytest.mark.asyncio
async def test_anthropic_stream_malformed_chunk_raises(loaded_engine: ConfigEngine) -> None:
    class BytesStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"data: not-json\n\n"

        async def aclose(self) -> None:
            return None

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=BytesStream())

    provider = AnthropicProvider.from_config_engine(loaded_engine, client=_client(handler))
    with pytest.raises(AnthropicMalformedResponseError):
        async for _ in provider.stream([ProviderMessage(role="user", content="hi")], model="claude-sonnet"):
            pass


@pytest.mark.asyncio
async def test_anthropic_error_mappings(loaded_engine: ConfigEngine) -> None:
    def handler_auth(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401)

    def handler_rate(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    provider_auth = AnthropicProvider.from_config_engine(loaded_engine, client=_client(handler_auth))
    provider_rate = AnthropicProvider.from_config_engine(loaded_engine, client=_client(handler_rate))

    with pytest.raises(AnthropicAuthError):
        await provider_auth.generate([ProviderMessage(role="user", content="hi")], model="claude-sonnet")
    with pytest.raises(AnthropicRateLimitError):
        await provider_rate.generate([ProviderMessage(role="user", content="hi")], model="claude-sonnet")


@pytest.mark.asyncio
async def test_anthropic_timeout_and_retry(loaded_engine: ConfigEngine) -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(500)
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}], "usage": {}})

    provider = AnthropicProvider.from_config_engine(loaded_engine, client=_client(handler))
    result = await provider.generate([ProviderMessage(role="user", content="hi")], model="claude-sonnet")
    assert result.content == "ok"
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_anthropic_timeout_exception(loaded_engine: ConfigEngine) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    provider = AnthropicProvider.from_config_engine(loaded_engine, client=_client(handler))
    with pytest.raises(AnthropicTimeoutError):
        await provider.generate([ProviderMessage(role="user", content="hi")], model="claude-sonnet")


@pytest.mark.asyncio
async def test_anthropic_model_validation(loaded_engine: ConfigEngine) -> None:
    provider = AnthropicProvider.from_config_engine(
        loaded_engine,
        client=_client(lambda request: httpx.Response(200, json={"content": [], "usage": {}})),
    )
    with pytest.raises(AnthropicModelUnavailableError):
        await provider.generate([ProviderMessage(role="user", content="hi")], model="unknown-model")


def test_anthropic_requires_env_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    engine = ConfigEngine(Path("smart_router/configs/default.yaml"))
    engine.load()
    with pytest.raises(AnthropicAuthError):
        AnthropicProvider.from_config_engine(engine)


def test_registry_and_protocol(loaded_engine: ConfigEngine) -> None:
    registry = ProviderRegistry()
    register_anthropic_provider(registry, loaded_engine)
    provider = registry.create("anthropic")
    assert isinstance(provider, ProviderAdapter)


@pytest.mark.asyncio
async def test_orchestrator_compatibility_stream_manager_provider_agnostic(loaded_engine: ConfigEngine) -> None:
    class BytesStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"type":"content_block_delta","delta":{"text":"hi"}}\n\n'
            yield b'data: {"type":"message_stop"}\n\n'

        async def aclose(self) -> None:
            return None

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/messages") and request.method == "POST":
            if b'"stream":true' in (request.content or b""):
                return httpx.Response(200, stream=BytesStream())
            return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}], "usage": {}})
        return httpx.Response(404)

    registry = ProviderRegistry()
    provider = AnthropicProvider.from_config_engine(loaded_engine, client=_client(handler))
    registry.register("anthropic", lambda: provider)
    orchestrator = ProviderOrchestrator(registry)

    non_stream = await orchestrator.execute(
        ExecutionRequest(
            provider="anthropic",
            model="claude-sonnet",
            messages=[ProviderMessage(role="user", content="hello")],
        )
    )
    assert non_stream.response.content == "ok"

    stream_events = []
    async for event in orchestrator.stream_execute(
        ExecutionRequest(
            provider="anthropic",
            model="claude-sonnet",
            messages=[ProviderMessage(role="user", content="hello")],
            stream=True,
        )
    ):
        stream_events.append(event.event_type)
    assert stream_events == ["stream_started", "token_chunk", "stream_completed"]


@pytest.mark.asyncio
async def test_interruption_hook_called(loaded_engine: ConfigEngine) -> None:
    called = {"ok": False}

    async def hook(request_id: str, reason: str) -> None:
        _ = request_id
        called["ok"] = reason.startswith("stream_cancelled")

    class CancelStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            raise asyncio.CancelledError()
            yield b""  # pragma: no cover

        async def aclose(self) -> None:
            return None

    provider = AnthropicProvider.from_config_engine(
        loaded_engine,
        client=_client(lambda request: httpx.Response(200, stream=CancelStream())),
        on_partial_recovery=hook,
    )

    with pytest.raises(asyncio.CancelledError):
        async for _ in provider.stream([ProviderMessage(role="user", content="hello")], model="claude-sonnet"):
            pass
    assert called["ok"] is True


@pytest.mark.asyncio
async def test_tool_use_preparation_hook(loaded_engine: ConfigEngine) -> None:
    observed = {"set": False}

    def tool_hook(payload: dict[str, object]) -> dict[str, object]:
        payload["metadata"] = {"tooling": "prepared"}
        observed["set"] = True
        return payload

    provider = AnthropicProvider.from_config_engine(
        loaded_engine,
        tool_use_preparation_hook=tool_hook,
        client=_client(lambda request: httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}], "usage": {}})),
    )

    assert observed["set"] is False
    # Hook is exercised on request construction inside generate.
    await provider.generate([ProviderMessage(role="user", content="hello")], model="claude-sonnet")
    assert observed["set"] is True
