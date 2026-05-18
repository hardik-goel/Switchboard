"""Interactive CLI loop helpers."""

from __future__ import annotations

import asyncio
import uuid

import typer

from smart_router.cli.commands.run import run_once
from smart_router.cli.bootstrap import AppServices


async def interactive_loop(services: AppServices) -> None:
    """Run interactive prompt loop with persistent session id."""
    session_id = f"sess-{uuid.uuid4().hex[:10]}"
    typer.echo(f"Interactive mode started (session={session_id}). Type 'exit' to quit.")

    while True:
        prompt = typer.prompt("smart-router")
        if prompt.strip().lower() in {"exit", "quit"}:
            break
        await run_once(services, prompt=prompt, session_id=session_id, stream=True)
        await asyncio.sleep(0)
