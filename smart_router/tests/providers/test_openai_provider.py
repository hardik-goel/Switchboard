from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from smart_router.core.config import ConfigEngine
from smart_router.core.interfaces.provider import ProviderAdapter
from smart_router.core.registry import ProviderRegistry
from smart_router.providers.openai import (
    OpenAIAuthError,
    OpenAIMalformedResponseError,
    OpenAIModelUnavailableError,
    OpenAIProvider,
    OpenAIRateLimitError,
    OpenAITimeoutError,
    OpenAITransientError,
    register_openai_provider,
)
from smart_router.schemas.provider import ProviderMessage


@pytest.fixture
def loaded_engine(monkeypatch: pytest.MonkeyPatch) -> ConfigEngine:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    engine = ConfigEngine(Path("smart_router/configs/default.yaml"))
    engine.load()
    return engine


def _client_with_handler(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


@pytest.mark.asyncio
async def test_openai_generate_normalizes_response(loaded_engine: ConfigEngine) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            },
        )

    provider = OpenAIProvider.from_config_engine(
        loaded_engine,
        client=_client_with_handler(httpx.MockTransport(handler)),
        session_id="s1",
    )
    response = await provider.generate(
        [ProviderMessage(role="user", content="hi")],
        model="gpt-5.4",
    )

    assert response.content == "hello"
    assert response.usage["input_tokens"] == 5
    assert response.usage["output_tokens"] == 3


@pytest.mark.asyncio
async def test_openai_stream_emits_normalized_events(loaded_engine: ConfigEngine) -> None:
    class BytesStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"choices":[{"delta":{"content":"hel"}}]}\n\n'
            yield b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
            yield b"data: [DONE]\n\n"

        async def aclose(self) -> None:
            return None

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=BytesStream())

    provider = OpenAIProvider.from_config_engine(
        loaded_engine,
        client=_client_with_handler(httpx.MockTransport(handler)),
    )
    events = []
    async for raw in provider.stream([ProviderMessage(role="user", content="hi")], model="gpt-5.4"):
        events.append(json.loads(raw))

    assert events[0]["content_delta"] == "hel"
    assert events[1]["content_delta"] == "lo"
    assert events[-1]["done"] is True


@pytest.mark.asyncio
async def test_openai_stream_malformed_chunk_raises(loaded_engine: ConfigEngine) -> None:
    class BytesStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"data: not-json\n\n"

        async def aclose(self) -> None:
            return None

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=BytesStream())

    provider = OpenAIProvider.from_config_engine(
        loaded_engine,
        client=_client_with_handler(httpx.MockTransport(handler)),
    )

    with pytest.raises(OpenAIMalformedResponseError):
        async for _ in provider.stream([ProviderMessage(role="user", content="hi")], model="gpt-5.4"):
            pass


@pytest.mark.asyncio
async def test_openai_health_check_success(loaded_engine: ConfigEngine) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": []})
        return httpx.Response(404)

    provider = OpenAIProvider.from_config_engine(
        loaded_engine,
        client=_client_with_handler(httpx.MockTransport(handler)),
    )
    assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_openai_maps_auth_error(loaded_engine: ConfigEngine) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    provider = OpenAIProvider.from_config_engine(
        loaded_engine,
        client=_client_with_handler(httpx.MockTransport(handler)),
    )

    with pytest.raises(OpenAIAuthError):
        await provider.generate([ProviderMessage(role="user", content="hi")], model="gpt-5.4")


@pytest.mark.asyncio
async def test_openai_maps_rate_limit_error(loaded_engine: ConfigEngine) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    provider = OpenAIProvider.from_config_engine(
        loaded_engine,
        client=_client_with_handler(httpx.MockTransport(handler)),
    )

    with pytest.raises(OpenAIRateLimitError):
        await provider.generate([ProviderMessage(role="user", content="hi")], model="gpt-5.4")


@pytest.mark.asyncio
async def test_openai_timeout_error(loaded_engine: ConfigEngine) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    provider = OpenAIProvider.from_config_engine(
        loaded_engine,
        client=_client_with_handler(httpx.MockTransport(handler)),
    )

    with pytest.raises(OpenAITimeoutError):
        await provider.generate([ProviderMessage(role="user", content="hi")], model="gpt-5.4")


@pytest.mark.asyncio
async def test_openai_model_validation(loaded_engine: ConfigEngine) -> None:
    provider = OpenAIProvider.from_config_engine(
        loaded_engine,
        client=_client_with_handler(httpx.MockTransport(lambda request: httpx.Response(200, json={}))),
    )
    with pytest.raises(OpenAIModelUnavailableError):
        await provider.generate([ProviderMessage(role="user", content="hi")], model="not-configured")


@pytest.mark.asyncio
async def test_openai_retry_safe_request_handling(loaded_engine: ConfigEngine) -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 2:
            return httpx.Response(500)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {}})

    provider = OpenAIProvider.from_config_engine(
        loaded_engine,
        client=_client_with_handler(httpx.MockTransport(handler)),
    )
    response = await provider.generate([ProviderMessage(role="user", content="hi")], model="gpt-5.4")
    assert response.content == "ok"
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_openai_transient_failure_exhausted(loaded_engine: ConfigEngine) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    provider = OpenAIProvider.from_config_engine(
        loaded_engine,
        client=_client_with_handler(httpx.MockTransport(handler)),
    )
    with pytest.raises(OpenAITransientError):
        await provider.generate([ProviderMessage(role="user", content="hi")], model="gpt-5.4")


@pytest.mark.asyncio
async def test_openai_malformed_generate_response_raises(loaded_engine: ConfigEngine) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    provider = OpenAIProvider.from_config_engine(
        loaded_engine,
        client=_client_with_handler(httpx.MockTransport(handler)),
    )
    with pytest.raises(OpenAIMalformedResponseError):
        await provider.generate([ProviderMessage(role="user", content="hi")], model="gpt-5.4")


def test_openai_requires_env_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    engine = ConfigEngine(Path("smart_router/configs/default.yaml"))
    engine.load()
    with pytest.raises(OpenAIAuthError):
        OpenAIProvider.from_config_engine(engine)


def test_registry_integration_and_protocol_compliance(loaded_engine: ConfigEngine) -> None:
    registry = ProviderRegistry()
    register_openai_provider(registry, loaded_engine)
    provider = registry.create("openai")
    assert isinstance(provider, ProviderAdapter)


@pytest.mark.asyncio
async def test_stream_graceful_interruption_hook_called(loaded_engine: ConfigEngine) -> None:
    hook_called = {"called": False}

    async def hook(request_id: str, reason: str) -> None:
        _ = request_id
        hook_called["called"] = reason.startswith("stream_cancelled")

    class CancelStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            raise asyncio.CancelledError()
            yield b""  # pragma: no cover

        async def aclose(self) -> None:
            return None

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=CancelStream())

    provider = OpenAIProvider.from_config_engine(
        loaded_engine,
        client=_client_with_handler(httpx.MockTransport(handler)),
        on_partial_recovery=hook,
    )

    with pytest.raises(asyncio.CancelledError):
        async for _ in provider.stream([ProviderMessage(role="user", content="hi")], model="gpt-5.4"):
            pass

    assert hook_called["called"] is True
