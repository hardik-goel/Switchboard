"""Production CLI entrypoint for Smart Router."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer

from smart_router.cli.bootstrap import build_services
from smart_router.cli.commands.config_cmd import config_validate
from smart_router.cli.commands.providers import providers_health
from smart_router.cli.commands.resume import resume_session
from smart_router.cli.commands.routes import explain_route
from smart_router.cli.commands.run import run_once
from smart_router.cli.commands.sessions import active_sessions, list_session, session_history
from smart_router.cli.commands.telemetry import telemetry_summary
from smart_router.cli.ui.interactive import interactive_loop

app = typer.Typer(help="Smart Router CLI")
routes_app = typer.Typer(help="Route inspection commands")
telemetry_app = typer.Typer(help="Telemetry commands")
providers_app = typer.Typer(help="Provider commands")
config_app = typer.Typer(help="Configuration commands")
sessions_app = typer.Typer(help="Session commands")

app.add_typer(routes_app, name="routes")
app.add_typer(telemetry_app, name="telemetry")
app.add_typer(providers_app, name="providers")
app.add_typer(config_app, name="config")
app.add_typer(sessions_app, name="sessions")

logger = logging.getLogger("smart_router.cli")


def _services(data_dir: Path | None = None):
    return build_services(data_dir=data_dir)


@app.command("run")
def run_command(prompt: str, session_id: str | None = None, stream: bool = True) -> None:
    """Run a single prompt through analyzer->router->execution lifecycle."""
    services = _services()
    asyncio.run(run_once(services, prompt=prompt, session_id=session_id, stream=stream))


@app.command("interactive")
def interactive_command() -> None:
    """Run interactive prompt loop."""
    services = _services()
    asyncio.run(interactive_loop(services))


@app.command("resume")
def resume_command(session_id: str) -> None:
    """Resume a previously interrupted session."""
    services = _services()
    asyncio.run(resume_session(services, session_id))


@routes_app.command("explain")
def routes_explain(prompt: str) -> None:
    """Explain route selection for a prompt without executing it."""
    services = _services()
    asyncio.run(explain_route(services, prompt))


@telemetry_app.command("summary")
def telemetry_summary_cmd() -> None:
    """Print telemetry analytics summary."""
    services = _services()
    asyncio.run(telemetry_summary(services))


@providers_app.command("health")
def providers_health_cmd() -> None:
    """Check provider connectivity/health."""
    services = _services()
    asyncio.run(providers_health(services))


@config_app.command("validate")
def config_validate_cmd() -> None:
    """Validate and inspect loaded config."""
    services = _services()
    config_validate(services)


@sessions_app.command("show")
def session_show_cmd(session_id: str) -> None:
    """Show active session metadata."""
    services = _services()
    asyncio.run(list_session(session_id, services))


@sessions_app.command("history")
def session_history_cmd(session_id: str) -> None:
    """Show session transition history."""
    services = _services()
    asyncio.run(session_history(session_id, services))


@sessions_app.command("active")
def session_active_cmd() -> None:
    """List active/resumable sessions."""
    services = _services()
    asyncio.run(active_sessions(services))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app()
