from __future__ import annotations

import json

import pytest

from smart_router.core.runtime import RuntimeExecutionContext
from smart_router.core.streaming import StreamManager


async def _provider_stream_ok():
    yield json.dumps({"content_delta": "hel", "done": False})
    yield json.dumps({"content_delta": "lo", "done": False})
    yield json.dumps({"done": True})


async def _provider_stream_broken():
    yield "not-json"


@pytest.mark.asyncio
async def test_stream_manager_partial_persistence_hook() -> None:
    snapshots: list[str] = []

    async def hook(context: RuntimeExecutionContext, partial: str) -> None:
        _ = context
        snapshots.append(partial)

    manager = StreamManager(partial_persistence_hook=hook)
    ctx = RuntimeExecutionContext(
        request_id="r1",
        session_id="s1",
        selected_provider="dummy",
        selected_model="m1",
    )

    events = []
    async for event in manager.run(provider_stream=_provider_stream_ok(), context=ctx, timeout_seconds=None):
        events.append(event.event_type)

    assert events == ["stream_started", "token_chunk", "token_chunk", "stream_completed"]
    assert snapshots == ["hel", "hello"]


@pytest.mark.asyncio
async def test_stream_manager_provider_error_event() -> None:
    manager = StreamManager()
    ctx = RuntimeExecutionContext(
        request_id="r2",
        session_id="s2",
        selected_provider="dummy",
        selected_model="m1",
    )

    events = []
    async for event in manager.run(provider_stream=_provider_stream_broken(), context=ctx, timeout_seconds=None):
        events.append(event.event_type)

    assert events == ["stream_started", "provider_error"]
