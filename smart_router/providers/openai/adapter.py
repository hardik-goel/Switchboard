"""OpenAI provider adapter implementation."""

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
    OpenAIAuthError,
    OpenAIMalformedResponseError,
    OpenAIModelUnavailableError,
    OpenAIProviderError,
    OpenAIRateLimitError,
    OpenAITimeoutError,
    OpenAITransientError,
)
from .schemas import OpenAIChatMessage, OpenAIChatRequest, OpenAIProviderConfig, OpenAIStreamEvent

logger = logging.getLogger("smart_router.providers.openai")

PartialRecoveryHook = Callable[[str, str], Awaitable[None]]


class OpenAIProvider:
    """Async OpenAI provider adapter conforming to ProviderAdapter contract."""

    name = "openai"

    def __init__(
        self,
        config: OpenAIProviderConfig,
        *,
        session_id: str | None = None,
        client: httpx.AsyncClient | None = None,
        on_partial_recovery: PartialRecoveryHook | None = None,
    ) -> None:
        self._config = config
        self._session_id = session_id
        self._client = client or httpx.AsyncClient(timeout=config.timeout_seconds)
        self._on_partial_recovery = on_partial_recovery

    @classmethod
    def from_config_engine(
        cls,
        config_engine: ConfigEngine,
        *,
        session_id: str | None = None,
        client: httpx.AsyncClient | None = None,
        on_partial_recovery: PartialRecoveryHook | None = None,
    ) -> "OpenAIProvider":
        """Construct provider from loaded application config."""
        provider_cfg = cls._extract_provider_config(config_engine)
        typed_cfg = cls.validate_config(provider_cfg)
        return cls(
            typed_cfg,
            session_id=session_id,
            client=client,
            on_partial_recovery=on_partial_recovery,
        )

    @staticmethod
    def _extract_provider_config(config_engine: ConfigEngine) -> ProviderConfig:
        app_config = config_engine.config
        provider_cfg = app_config.providers.get("openai")
        if provider_cfg is None:
            raise OpenAIProviderError("OpenAI provider config missing from app config.")
        return provider_cfg

    @classmethod
    def validate_config(cls, provider_config: ProviderConfig) -> OpenAIProviderConfig:
        """Validate and normalize OpenAI provider configuration."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise OpenAIAuthError("OPENAI_API_KEY is required for OpenAI provider.")

        settings = provider_config.settings
        timeout_seconds = float(settings.get("timeout_seconds", 30.0))
        max_retries = int(settings.get("max_retries", 2))
        enabled_models = {model.name for model in provider_config.models}
        default_model = next(iter(enabled_models), None)

        return OpenAIProviderConfig(
            api_key=api_key,
            api_base=(provider_config.api_base or "https://api.openai.com/v1").rstrip("/"),
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
        """Generate a non-streaming response from OpenAI."""
        self._validate_model(model)
        request_id = str(uuid.uuid4())
        payload = self._build_request_payload(messages, model=model, temperature=temperature, stream=False)

        start = time.perf_counter()
        response_json = await self._request_with_retry(
            endpoint="/chat/completions",
            payload=payload,
            request_id=request_id,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        normalized = self._normalize_generate_response(response_json, model=model)

        logger.info(
            "provider_generate_success",
            extra={
                "provider": self.name,
                "model": model,
                "latency": latency_ms,
                "request_id": request_id,
                "session_id": self._session_id,
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
        """Stream normalized provider-agnostic events encoded as JSON lines."""
        self._validate_model(model)
        request_id = str(uuid.uuid4())
        payload = self._build_request_payload(messages, model=model, temperature=temperature, stream=True)
        start = time.perf_counter()
        partial_text = ""

        try:
            async with self._client.stream(
                "POST",
                f"{self._config.api_base}/chat/completions",
                headers=self._auth_headers(),
                json=payload,
                timeout=self._config.timeout_seconds,
            ) as response:
                self._raise_for_status(response.status_code)
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        done_event = OpenAIStreamEvent(
                            event_type="chunk",
                            provider=self.name,
                            model=model,
                            request_id=request_id,
                            done=True,
                        )
                        yield done_event.model_dump_json()
                        break

                    parsed = self._safe_json_load(data)
                    chunk = self._extract_stream_delta(parsed)
                    if chunk:
                        partial_text += chunk
                        event = OpenAIStreamEvent(
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
            raise OpenAITimeoutError("OpenAI stream timed out.") from exc
        except httpx.HTTPError as exc:
            if self._on_partial_recovery is not None:
                await self._on_partial_recovery(request_id, f"stream_transport_error:{partial_text}")
            raise OpenAITransientError("OpenAI stream failed due to transport error.") from exc
        except OpenAIMalformedResponseError:
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
                    "latency": latency_ms,
                    "request_id": request_id,
                    "session_id": self._session_id,
                    "token_estimates": {},
                },
            )

    async def health_check(self) -> bool:
        """Check OpenAI provider availability and auth validity."""
        try:
            response = await self._client.get(
                f"{self._config.api_base}/models",
                headers=self._auth_headers(),
                timeout=self._config.timeout_seconds,
            )
            if response.status_code == 200:
                return True
            self._raise_for_status(response.status_code)
        except OpenAIProviderError:
            return False
        except httpx.HTTPError:
            return False
        return False

    def _build_request_payload(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        temperature: float,
        stream: bool,
    ) -> dict[str, Any]:
        normalized_messages = [
            OpenAIChatMessage(role=message.role, content=message.content) for message in messages
        ]
        request = OpenAIChatRequest(
            model=model,
            messages=normalized_messages,
            temperature=temperature,
            stream=stream,
        )
        return request.model_dump()

    def _normalize_generate_response(self, payload: dict[str, Any], *, model: str) -> ProviderResponse:
        try:
            choices = payload["choices"]
            first = choices[0]
            message = first["message"]
            content = message["content"]
            usage = payload.get("usage") or {}
            usage_map = {
                "input_tokens": int(usage.get("prompt_tokens", 0)),
                "output_tokens": int(usage.get("completion_tokens", 0)),
                "total_tokens": int(usage.get("total_tokens", 0)),
            }
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise OpenAIMalformedResponseError("Malformed OpenAI completion response.") from exc

        return ProviderResponse(
            content=content,
            model=model,
            usage=usage_map,
            metadata={"provider": self.name},
        )

    async def _request_with_retry(
        self,
        *,
        endpoint: str,
        payload: dict[str, Any],
        request_id: str,
    ) -> dict[str, Any]:
        attempts = self._config.max_retries + 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.post(
                    f"{self._config.api_base}{endpoint}",
                    headers=self._auth_headers(),
                    json=payload,
                    timeout=self._config.timeout_seconds,
                )
                self._raise_for_status(response.status_code)
                return response.json()
            except OpenAITransientError as exc:
                last_error = exc
                logger.warning(
                    "provider_retry_attempt",
                    extra={
                        "provider": self.name,
                        "request_id": request_id,
                        "attempt": attempt,
                        "max_attempts": attempts,
                    },
                )
                if attempt < attempts:
                    await asyncio.sleep(0.2 * attempt)
                    continue
                break
            except httpx.TimeoutException as exc:
                raise OpenAITimeoutError("OpenAI request timed out.") from exc
            except httpx.HTTPError as exc:
                raise OpenAITransientError("OpenAI transport error.") from exc

        raise OpenAITransientError("OpenAI request failed after retries.") from last_error

    def _validate_model(self, model: str) -> None:
        if model not in self._config.enabled_models:
            raise OpenAIModelUnavailableError(f"Model not enabled for OpenAI provider: {model}")

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._config.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

    def _raise_for_status(self, status_code: int) -> None:
        if status_code in (401, 403):
            raise OpenAIAuthError("OpenAI authentication failed.")
        if status_code == 429:
            raise OpenAIRateLimitError("OpenAI rate limit exceeded.")
        if status_code == 404:
            raise OpenAIModelUnavailableError("OpenAI model or endpoint unavailable.")
        if status_code >= 500:
            raise OpenAITransientError(f"OpenAI server error ({status_code}).")
        if status_code >= 400:
            raise OpenAIProviderError(f"OpenAI request failed with status {status_code}.")

    def _safe_json_load(self, value: str) -> dict[str, Any]:
        try:
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValueError("Not a JSON object")
            return parsed
        except (json.JSONDecodeError, ValueError) as exc:
            raise OpenAIMalformedResponseError("Malformed OpenAI stream chunk.") from exc

    def _extract_stream_delta(self, payload: dict[str, Any]) -> str:
        try:
            choices = payload.get("choices") or []
            if not choices:
                return ""
            delta = choices[0].get("delta") or {}
            content = delta.get("content") or ""
            return content if isinstance(content, str) else ""
        except (AttributeError, IndexError, TypeError):
            return ""

    async def aclose(self) -> None:
        """Close underlying HTTP client resources."""
        await self._client.aclose()


def register_openai_provider(registry: ProviderRegistry, config_engine: ConfigEngine) -> None:
    """Register OpenAI provider factory into registry using app config."""

    def factory() -> OpenAIProvider:
        return OpenAIProvider.from_config_engine(config_engine)

    registry.register("openai", factory)
