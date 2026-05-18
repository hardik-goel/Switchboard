"""Streaming coordinator for provider-agnostic event normalization."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable

from smart_router.core.runtime import RuntimeExecutionContext

from .events import StreamEvent

logger = logging.getLogger("smart_router.streaming.manager")

PartialPersistenceHook = Callable[[RuntimeExecutionContext, str], Awaitable[None]]


class StreamManager:
    """Normalize provider stream chunks into runtime lifecycle events."""

    def __init__(
        self,
        *,
        partial_persistence_hook: PartialPersistenceHook | None = None,
    ) -> None:
        self._partial_persistence_hook = partial_persistence_hook

    async def run(
        self,
        *,
        provider_stream: AsyncIterator[str],
        context: RuntimeExecutionContext,
        timeout_seconds: float | None,
    ) -> AsyncIterator[StreamEvent]:
        """Run streaming lifecycle and emit normalized events."""
        context.stream_state.is_streaming = True
        start = StreamEvent(
            event_type="stream_started",
            request_id=context.request_id,
            session_id=context.session_id,
            provider=context.selected_provider,
            model=context.selected_model,
            retry_count=context.retry_count,
            stream_state="active",
        )
        yield start

        partial_content = ""
        try:
            async for raw in self._iterate(provider_stream, timeout_seconds):
                if context.cancellation_state.is_cancelled:
                    raise asyncio.CancelledError()

                event = self._normalize_event(raw, context)
                context.stream_state.last_event_type = event.event_type

                if event.event_type == "token_chunk":
                    partial_content += event.content
                    if self._partial_persistence_hook is not None:
                        await self._partial_persistence_hook(context, partial_content)

                if event.event_type == "stream_completed":
                    context.stream_state.is_completed = True

                yield event
        except asyncio.TimeoutError:
            context.stream_state.last_event_type = "stream_interrupted"
            yield StreamEvent(
                event_type="stream_interrupted",
                request_id=context.request_id,
                session_id=context.session_id,
                provider=context.selected_provider,
                model=context.selected_model,
                retry_count=context.retry_count,
                stream_state="timeout",
            )
        except asyncio.CancelledError:
            context.stream_state.last_event_type = "stream_interrupted"
            yield StreamEvent(
                event_type="stream_interrupted",
                request_id=context.request_id,
                session_id=context.session_id,
                provider=context.selected_provider,
                model=context.selected_model,
                retry_count=context.retry_count,
                stream_state="cancelled",
            )
        except Exception as exc:
            context.stream_state.last_event_type = "provider_error"
            logger.exception("stream_manager_provider_error", extra={"request_id": context.request_id})
            yield StreamEvent(
                event_type="provider_error",
                request_id=context.request_id,
                session_id=context.session_id,
                provider=context.selected_provider,
                model=context.selected_model,
                retry_count=context.retry_count,
                stream_state="error",
                metadata={"error": str(exc)},
            )
        finally:
            context.stream_state.is_streaming = False

    async def _iterate(
        self,
        provider_stream: AsyncIterator[str],
        timeout_seconds: float | None,
    ) -> AsyncIterator[str]:
        while True:
            try:
                if timeout_seconds is None:
                    item = await provider_stream.__anext__()
                else:
                    item = await asyncio.wait_for(provider_stream.__anext__(), timeout_seconds)
                yield item
            except StopAsyncIteration:
                break

    def _normalize_event(self, raw: str, context: RuntimeExecutionContext) -> StreamEvent:
        payload = json.loads(raw)
        content_delta = payload.get("content_delta", "")
        done = bool(payload.get("done", False))

        if done:
            return StreamEvent(
                event_type="stream_completed",
                request_id=context.request_id,
                session_id=context.session_id,
                provider=context.selected_provider,
                model=context.selected_model,
                retry_count=context.retry_count,
                stream_state="completed",
            )

        return StreamEvent(
            event_type="token_chunk",
            request_id=context.request_id,
            session_id=context.session_id,
            provider=context.selected_provider,
            model=context.selected_model,
            content=content_delta,
            retry_count=context.retry_count,
            stream_state="active",
        )
