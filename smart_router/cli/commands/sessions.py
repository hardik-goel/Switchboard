"""Session inspection commands."""

from __future__ import annotations

import json

import typer

from smart_router.cli.bootstrap import AppServices


async def list_session(session_id: str, services: AppServices) -> None:
    record = await services.session_manager.restore_session(session_id)
    if record is None:
        typer.echo("Session not found")
        return
    typer.echo(json.dumps(record.model_dump(), indent=2))


async def session_history(session_id: str, services: AppServices) -> None:
    transitions = await services.persistence.restore_transitions(session_id)
    typer.echo(json.dumps([t.model_dump() for t in transitions], indent=2))


async def active_sessions(services: AppServices) -> None:
    sessions = await services.persistence.list_sessions()
    rows = [s.model_dump() for s in sessions if s.lifecycle_state not in ("completed", "failed", "archived")]
    typer.echo(json.dumps(rows, indent=2))
