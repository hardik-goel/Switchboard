"""Resume command implementation."""

from __future__ import annotations

import typer

from smart_router.cli.bootstrap import AppServices
from smart_router.cli.rendering.console import render_execution_outcome


async def resume_session(services: AppServices, session_id: str) -> None:
    plan = await services.recovery.recover_plan(session_id)
    if plan is None:
        typer.echo(f"No resumable plan found for session {session_id}")
        return

    await services.recovery.mark_resumed(session_id)
    outcome = await services.lifecycle.execute(plan)
    render_execution_outcome(outcome)
