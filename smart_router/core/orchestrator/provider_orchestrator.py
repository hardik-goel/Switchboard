"""Provider orchestrator for runtime execution pipeline."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from smart_router.core.registry import ProviderRegistry, ProviderRegistryError
from smart_router.core.runtime import RuntimeExecutionContext
from smart_router.core.streaming import StreamEvent, StreamManager
from smart_router.core.telemetry import maybe_emit
from smart_router.core.persistence import maybe_persist

from .exceptions import (
    ExecutionFailureError,
    InvalidExecutionRequestError,
    ProviderUnavailableError,
    RuntimeCancellationError,
    StreamFailureError,
)
from .schemas import ExecutionRequest, ExecutionResult

logger = logging.getLogger("smart_router.orchestrator")
TelemetryHook = Callable[[dict[str, Any]], Awaitable[None] | None]
PersistenceHook = Callable[[dict[str, Any]], Awaitable[None] | None]


class ProviderOrchestrator:
    """Runtime orchestrator that executes provider calls without routing logic."""

    def __init__(
        self,
        registry: ProviderRegistry,
        *,
        stream_manager: StreamManager | None = None,
        max_retries: int = 0,
        telemetry_hook: TelemetryHook | None = None,
        persistence_hook: PersistenceHook | None = None,
    ) -> None:
        self._registry = registry
        self._stream_manager = stream_manager or StreamManager()
        self._max_retries = max_retries
        self._cancellations: dict[str, RuntimeExecutionContext] = {}
        self._telemetry_hook = telemetry_hook
        self._persistence_hook = persistence_hook

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute non-streaming provider request with retry-safe wrapper."""
        self._validate_request(request)
        context = self._new_context(request)
        self._cancellations[context.request_id] = context

        start = time.perf_counter()
        try:
            provider = self._resolve_provider(request.provider)
            result = await self._execute_with_retries(provider, request, context)
            latency_ms = int((time.perf_counter() - start) * 1000)

            logger.info(
                "orchestrator_execute_success",
                extra={
                    "request_id": context.request_id,
                    "session_id": context.session_id,
                    "provider": context.selected_provider,
                    "model": context.selected_model,
                    "latency": latency_ms,
                    "retry_count": context.retry_count,
                    "stream_state": context.stream_state.last_event_type,
                },
            )
            await maybe_emit(
                self._telemetry_hook,
                {
                    "event_type": "execution_completed",
                    "request_id": context.request_id,
                    "session_id": context.session_id,
                    "provider": context.selected_provider,
                    "model": context.selected_model,
                    "latency": latency_ms,
                    "retry_count": context.retry_count,
                    "execution_state": "completed",
                },
            )
            await maybe_persist(
                self._persistence_hook,
                {
                    "event_type": "execution_completed",
                    "request_id": context.request_id,
                    "session_id": context.session_id,
                    "provider": context.selected_provider,
                    "model": context.selected_model,
                    "latency": latency_ms,
                    "retry_count": context.retry_count,
                    "execution_state": "completed",
                },
            )
            return ExecutionResult(
                request_id=context.request_id,
                provider=context.selected_provider,
                model=context.selected_model,
                response=result,
                latency_ms=latency_ms,
                retry_count=context.retry_count,
            )
        except RuntimeCancellationError:
            raise
        except Exception as exc:
            await maybe_emit(
                self._telemetry_hook,
                {
                    "event_type": "execution_failed",
                    "request_id": context.request_id,
                    "session_id": context.session_id,
                    "provider": context.selected_provider,
                    "model": context.selected_model,
                    "retry_count": context.retry_count,
                    "execution_state": "failed",
                    "metadata": {"error": str(exc)},
                },
            )
            await maybe_persist(
                self._persistence_hook,
                {
                    "event_type": "execution_failed",
                    "request_id": context.request_id,
                    "session_id": context.session_id,
                    "provider": context.selected_provider,
                    "model": context.selected_model,
                    "retry_count": context.retry_count,
                    "execution_state": "failed",
                    "metadata": {"error": str(exc)},
                },
            )
            raise ExecutionFailureError(f"Provider execution failed: {exc}") from exc
        finally:
            self._cancellations.pop(context.request_id, None)

    async def stream_execute(self, request: ExecutionRequest) -> AsyncIterator[StreamEvent]:
        """Execute streaming provider request and emit normalized lifecycle events."""
        self._validate_request(request)
        context = self._new_context(request)
        context.stream_state.is_streaming = True
        self._cancellations[context.request_id] = context

        try:
            provider = self._resolve_provider(request.provider)
            provider_stream = provider.stream(
                request.messages,
                model=request.model,
                temperature=request.temperature,
            )
            async for event in self._stream_manager.run(
                provider_stream=provider_stream,
                context=context,
                timeout_seconds=request.timeout_seconds,
            ):
                logger.info(
                    "orchestrator_stream_event",
                    extra={
                        "request_id": context.request_id,
                        "session_id": context.session_id,
                        "provider": context.selected_provider,
                        "model": context.selected_model,
                        "latency": 0,
                        "retry_count": context.retry_count,
                        "stream_state": event.stream_state,
                    },
                )
                if event.event_type == "stream_interrupted":
                    await maybe_emit(
                        self._telemetry_hook,
                        {
                            "event_type": "stream_interrupted",
                            "request_id": context.request_id,
                            "session_id": context.session_id,
                            "provider": context.selected_provider,
                            "model": context.selected_model,
                            "retry_count": context.retry_count,
                            "execution_state": event.stream_state,
                        },
                    )
                yield event
        except RuntimeCancellationError:
            raise
        except Exception as exc:
            raise StreamFailureError(f"Provider streaming failed: {exc}") from exc
        finally:
            self._cancellations.pop(context.request_id, None)

    def cancel(self, request_id: str, *, reason: str = "cancelled") -> None:
        """Signal cancellation for active execution/stream."""
        context = self._cancellations.get(request_id)
        if context is None:
            return
        context.cancellation_state.is_cancelled = True
        context.cancellation_state.reason = reason

    def _new_context(self, request: ExecutionRequest) -> RuntimeExecutionContext:
        return RuntimeExecutionContext(
            request_id=request.request_id or str(uuid.uuid4()),
            session_id=request.session_id,
            selected_provider=request.provider,
            selected_model=request.model,
            token_estimates=request.token_estimates,
            execution_metadata={"stream": request.stream},
        )

    def _resolve_provider(self, provider_name: str):
        try:
            provider = self._registry.create(provider_name)
        except ProviderRegistryError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        return provider

    async def _execute_with_retries(self, provider, request: ExecutionRequest, context: RuntimeExecutionContext):
        last_error: Exception | None = None
        attempts = self._max_retries + 1

        for attempt in range(1, attempts + 1):
            if context.cancellation_state.is_cancelled:
                raise RuntimeCancellationError(context.cancellation_state.reason or "cancelled")
            try:
                response = await asyncio.wait_for(
                    provider.generate(
                        request.messages,
                        model=request.model,
                        temperature=request.temperature,
                    ),
                    timeout=request.timeout_seconds,
                )
                return response
            except asyncio.TimeoutError as exc:
                last_error = exc
            except Exception as exc:
                last_error = exc

            context.retry_count = attempt
            if attempt < attempts:
                await asyncio.sleep(0.1 * attempt)

        raise ExecutionFailureError("Execution failed after retries.") from last_error

    def _validate_request(self, request: ExecutionRequest) -> None:
        if not request.messages:
            raise InvalidExecutionRequestError("Execution request must include at least one message.")
