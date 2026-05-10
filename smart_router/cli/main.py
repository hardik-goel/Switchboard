"""CLI entrypoint for Smart Router."""

from __future__ import annotations

import json
import logging

import typer

from smart_router.schemas.prompt import PromptRequest

app = typer.Typer(help="Smart Router CLI")
logger = logging.getLogger("smart_router.cli")


@app.command("route")
def route_prompt(prompt: str, session_id: str | None = None) -> None:
    """Validate request shape and hand off to orchestration layer."""
    request = PromptRequest(prompt=prompt, session_id=session_id)
    logger.info("route_request_received", extra={"session_id": request.session_id})
    typer.echo(json.dumps(request.model_dump(), indent=2))


if __name__ == "__main__":
    app()
