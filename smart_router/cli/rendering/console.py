"""Terminal rendering helpers for CLI UX."""

from __future__ import annotations

import json

import typer

from smart_router.core.execution.schemas import FinalExecutionOutcome
from smart_router.core.streaming import StreamEvent
from smart_router.schemas.routing import RoutingDecision


def render_route_explanation(decision: RoutingDecision) -> None:
    typer.echo("Route Selection")
    typer.echo(f"  Provider: {decision.selected_provider}")
    typer.echo(f"  Model: {decision.selected_model}")
    typer.echo(f"  Reason: {decision.reasoning_summary}")
    typer.echo(f"  Latency(ms est): {decision.estimated_latency:.1f}")
    typer.echo(f"  Cost(est): {decision.estimated_cost:.4f}")
    typer.echo(f"  Fallbacks: {', '.join(decision.fallback_chain) if decision.fallback_chain else 'None'}")


def render_execution_outcome(outcome: FinalExecutionOutcome) -> None:
    typer.echo("Execution Outcome")
    typer.echo(f"  State: {outcome.snapshot.state}")
    typer.echo(f"  Provider: {outcome.snapshot.active_provider}")
    typer.echo(f"  Model: {outcome.snapshot.active_model}")
    typer.echo(f"  Retry count: {outcome.snapshot.retry_count}")
    typer.echo(f"  Fallback provider: {outcome.snapshot.fallback_provider or 'None'}")
    if outcome.result is not None:
        typer.echo("Response")
        typer.echo(outcome.result.response.content)
    if outcome.failure_reason:
        typer.echo(f"Failure: {outcome.failure_reason}")


def render_stream_event(event: StreamEvent) -> None:
    if event.event_type == "stream_started":
        typer.echo(f"[stream] started provider={event.provider} model={event.model}")
    elif event.event_type == "token_chunk":
        typer.echo(event.content, nl=False)
    elif event.event_type == "stream_completed":
        typer.echo("\n[stream] completed")
    elif event.event_type == "stream_interrupted":
        typer.echo(f"\n[stream] interrupted ({event.stream_state})")
    elif event.event_type == "provider_error":
        typer.echo(f"\n[stream] provider_error: {json.dumps(event.metadata)}")


def render_telemetry_summary(summary: dict[str, object]) -> None:
    typer.echo(json.dumps(summary, indent=2, default=str))


def render_provider_health(health: dict[str, object]) -> None:
    typer.echo(json.dumps(health, indent=2, default=str))
