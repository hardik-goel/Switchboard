"""Anthropic provider adapter implementation."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any

import httpx

from smart_router.core.config import ConfigEngine
from smart_router.core.registry import ProviderRegistry
from smart_router.schemas.config import ProviderConfig
from smart_router.schemas.provider import ProviderMessage, ProviderResponse

from .exceptions import (
    AnthropicAuthError,
    AnthropicMalformedResponseError,
    AnthropicModelUnavailableError,
    AnthropicProviderError,
    AnthropicRateLimitError,
    AnthropicTimeoutError,
    AnthropicTransientError,
)
from .schemas import (
    AnthropicGenerateRequest,
    AnthropicMessageItem,
    AnthropicProviderConfig,
    AnthropicStreamEvent,
)

logger = logging.getLogger("smart_router.providers.anthropic")

PartialRecoveryHook = Callable[[str, str], Awaitable[None]]
ToolUsePreparationHook = Callable[[dict[str, Any]], dict[str, Any]]


class AnthropicProvider:
    """Async Anthropic provider adapter conforming to provider contract."""

    name = "anthropic"

    def __init__(
        self,
        config: AnthropicProviderConfig,
        *,
        session_id: str | None = None,
        client: httpx.AsyncClient | None = None,
        on_partial_recovery: PartialRecoveryHook | None = None,
        tool_use_preparation_hook: ToolUsePreparationHook | None = None,
    ) -> None:
        self._config = config
        self._session_id = session_id
        self._client = client or httpx.AsyncClient(timeout=config.timeout_seconds)
        self._on_partial_recovery = on_partial_recovery
        self._tool_use_preparation_hook = tool_use_preparation_hook

    @classmethod
    def from_config_engine(
        cls,
        config_engine: ConfigEngine,
        *,
        session_id: str | None = None,
        client: httpx.AsyncClient | None = None,
        on_partial_recovery: PartialRecoveryHook | None = None,
        tool_use_preparation_hook: ToolUsePreparationHook | None = None,
    ) -> "AnthropicProvider":
        provider_cfg = cls._extract_provider_config(config_engine)
        typed_cfg = cls.validate_config(provider_cfg)
        return cls(
            typed_cfg,
            session_id=session_id,
            client=client,
            on_partial_recovery=on_partial_recovery,
            tool_use_preparation_hook=tool_use_preparation_hook,
        )

    @staticmethod
    def _extract_provider_config(config_engine: ConfigEngine) -> ProviderConfig:
        provider_cfg = config_engine.config.providers.get("anthropic")
        if provider_cfg is None:
            raise AnthropicProviderError("Anthropic provider config missing from app config.")
        return provider_cfg

    @classmethod
    def validate_config(cls, provider_config: ProviderConfig) -> AnthropicProviderConfig:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise AnthropicAuthError("ANTHROPIC_API_KEY is required for Anthropic provider.")

        settings = provider_config.settings
        timeout_seconds = float(settings.get("timeout_seconds", 30.0))
        max_retries = int(settings.get("max_retries", 2))
        enabled_models = {model.name for model in provider_config.models}
        default_model = next(iter(enabled_models), None)

        return AnthropicProviderConfig(
            api_key=api_key,
            api_base=(provider_config.api_base or "https://api.anthropic.com/v1").rstrip("/"),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            default_model=default_model,
            enabled_models=enabled_models,
        )

    async def generate(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        temperature: float = 0.0,
    ) -> ProviderResponse:
        self._validate_model(model)
        request_id = str(uuid.uuid4())
        payload = self._build_request_payload(messages, model=model, temperature=temperature, stream=False)
        if self._tool_use_preparation_hook is not None:
            payload = self._tool_use_preparation_hook(payload)

        start = time.perf_counter()
        response_json = await self._request_with_retry(request_id=request_id, payload=payload)
        latency_ms = int((time.perf_counter() - start) * 1000)
        normalized = self._normalize_generate_response(response_json, model=model)

        logger.info(
            "provider_generate_success",
            extra={
                "provider": self.name,
                "model": model,
                "request_id": request_id,
                "session_id": self._session_id,
                "latency": latency_ms,
                "retry_count": 0,
                "stream_state": "none",
                "token_estimates": normalized.usage,
            },
        )
        return normalized

    async def stream(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]:
        self._validate_model(model)
        request_id = str(uuid.uuid4())
        payload = self._build_request_payload(messages, model=model, temperature=temperature, stream=True)
        if self._tool_use_preparation_hook is not None:
            payload = self._tool_use_preparation_hook(payload)

        start = time.perf_counter()
        partial_text = ""
        try:
            async with self._client.stream(
                "POST",
                f"{self._config.api_base}/messages",
                headers=self._headers(),
                json=payload,
                timeout=self._config.timeout_seconds,
            ) as response:
                self._raise_for_status(response.status_code)
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("event:"):
                        continue
                    if not line.startswith("data:"):
                        continue

                    parsed = self._safe_json_load(line.removeprefix("data:").strip())
                    event_type = parsed.get("type", "")

                    if event_type == "message_stop":
                        done = AnthropicStreamEvent(
                            event_type="chunk",
                            provider=self.name,
                            model=model,
                            request_id=request_id,
                            done=True,
                        )
                        yield done.model_dump_json()
                        break

                    chunk = self._extract_stream_delta(parsed)
                    if chunk:
                        partial_text += chunk
                        event = AnthropicStreamEvent(
                            event_type="chunk",
                            provider=self.name,
                            model=model,
                            request_id=request_id,
                            content_delta=chunk,
                        )
                        yield event.model_dump_json()
        except asyncio.CancelledError:
            if self._on_partial_recovery is not None:
                await self._on_partial_recovery(request_id, f"stream_cancelled:{partial_text}")
            raise
        except httpx.TimeoutException as exc:
            if self._on_partial_recovery is not None:
                await self._on_partial_recovery(request_id, f"stream_timeout:{partial_text}")
            raise AnthropicTimeoutError("Anthropic stream timed out.") from exc
        except httpx.HTTPError as exc:
            if self._on_partial_recovery is not None:
                await self._on_partial_recovery(request_id, f"stream_transport_error:{partial_text}")
            raise AnthropicTransientError("Anthropic stream transport failure.") from exc
        except AnthropicMalformedResponseError:
            if self._on_partial_recovery is not None:
                await self._on_partial_recovery(request_id, f"stream_malformed_chunk:{partial_text}")
            raise
        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "provider_stream_finished",
                extra={
                    "provider": self.name,
                    "model": model,
                    "request_id": request_id,
                    "session_id": self._session_id,
                    "latency": latency_ms,
                    "retry_count": 0,
                    "stream_state": "finished",
                    "token_estimates": {},
                },
            )

    async def health_check(self) -> bool:
        try:
            response = await self._client.post(
                f"{self._config.api_base}/messages",
                headers=self._headers(),
                json={
                    "model": self._config.default_model or "claude-sonnet",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "ping"}],
                },
                timeout=self._config.timeout_seconds,
            )
            if response.status_code in (200, 400):
                return True
            self._raise_for_status(response.status_code)
        except AnthropicProviderError:
            return False
        except httpx.HTTPError:
            return False
        return False

    async def aclose(self) -> None:
        await self._client.aclose()

    def _build_request_payload(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        temperature: float,
        stream: bool,
    ) -> dict[str, Any]:
        req = AnthropicGenerateRequest(
            model=model,
            temperature=temperature,
            messages=[AnthropicMessageItem(role=m.role, content=m.content) for m in messages],
            stream=stream,
        )
        return req.model_dump()

    def _normalize_generate_response(self, payload: dict[str, Any], *, model: str) -> ProviderResponse:
        try:
            content_items = payload["content"]
            text = "".join(item.get("text", "") for item in content_items if item.get("type") == "text")
            usage = payload.get("usage") or {}
            usage_map = {
                "input_tokens": int(usage.get("input_tokens", 0)),
                "output_tokens": int(usage.get("output_tokens", 0)),
                "total_tokens": int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0)),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise AnthropicMalformedResponseError("Malformed Anthropic completion response.") from exc

        return ProviderResponse(
            content=text,
            model=model,
            usage=usage_map,
            metadata={"provider": self.name},
        )

    async def _request_with_retry(self, *, request_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        attempts = self._config.max_retries + 1
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.post(
                    f"{self._config.api_base}/messages",
                    headers=self._headers(),
                    json=payload,
                    timeout=self._config.timeout_seconds,
                )
                self._raise_for_status(response.status_code)
                return response.json()
            except AnthropicTransientError as exc:
                last_error = exc
                logger.warning(
                    "provider_retry_attempt",
                    extra={
                        "provider": self.name,
                        "request_id": request_id,
                        "retry_count": attempt,
                        "stream_state": "none",
                    },
                )
                if attempt < attempts:
                    await asyncio.sleep(0.2 * attempt)
                    continue
                break
            except httpx.TimeoutException as exc:
                raise AnthropicTimeoutError("Anthropic request timed out.") from exc
            except httpx.HTTPError as exc:
                raise AnthropicTransientError("Anthropic transport error.") from exc

        raise AnthropicTransientError("Anthropic request failed after retries.") from last_error

    def _validate_model(self, model: str) -> None:
        if model not in self._config.enabled_models:
            raise AnthropicModelUnavailableError(f"Model not enabled for Anthropic provider: {model}")

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._config.api_key.get_secret_value(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _raise_for_status(self, status_code: int) -> None:
        if status_code in (401, 403):
            raise AnthropicAuthError("Anthropic authentication failed.")
        if status_code == 429:
            raise AnthropicRateLimitError("Anthropic rate limit exceeded.")
        if status_code == 404:
            raise AnthropicModelUnavailableError("Anthropic model or endpoint unavailable.")
        if status_code >= 500:
            raise AnthropicTransientError(f"Anthropic server error ({status_code}).")
        if status_code >= 400:
            raise AnthropicProviderError(f"Anthropic request failed with status {status_code}.")

    def _safe_json_load(self, value: str) -> dict[str, Any]:
        try:
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValueError("not object")
            return parsed
        except (json.JSONDecodeError, ValueError) as exc:
            raise AnthropicMalformedResponseError("Malformed Anthropic stream chunk.") from exc

    def _extract_stream_delta(self, payload: dict[str, Any]) -> str:
        try:
            if payload.get("type") != "content_block_delta":
                return ""
            delta = payload.get("delta") or {}
            text = delta.get("text") or ""
            return text if isinstance(text, str) else ""
        except (TypeError, AttributeError):
            return ""


def register_anthropic_provider(registry: ProviderRegistry, config_engine: ConfigEngine) -> None:
    """Register Anthropic provider factory into provider registry."""

    def factory() -> AnthropicProvider:
        return AnthropicProvider.from_config_engine(config_engine)

    registry.register("anthropic", factory)
