"""Run command implementation."""

from __future__ import annotations

import logging
import uuid

import typer

from smart_router.cli.bootstrap import AppServices
from smart_router.cli.rendering.console import render_execution_outcome, render_route_explanation, render_stream_event
from smart_router.core.analyzer import AnalyzerExecutionContext
from smart_router.core.execution.schemas import ExecutionPlan
from smart_router.core.sessions import ContextSnapshot
from smart_router.schemas.prompt import PromptRequest
from smart_router.schemas.provider import ProviderMessage

logger = logging.getLogger("smart_router.cli.run")


async def run_once(services: AppServices, *, prompt: str, session_id: str | None, stream: bool) -> None:
    request_id = f"req-{uuid.uuid4().hex[:12]}"
    actual_session_id = session_id or f"sess-{uuid.uuid4().hex[:12]}"

    existing = await services.session_manager.restore_session(actual_session_id)
    if existing is None:
        await services.session_manager.create_session(session_id=actual_session_id, request_id=request_id)
    else:
        existing.request_id = request_id
        await services.session_manager.update_session(existing)

    prompt_request = PromptRequest(prompt=prompt, session_id=actual_session_id)
    classification = await services.analyzer.analyze(
        prompt,
        execution_context=AnalyzerExecutionContext(request_id=request_id, session_id=actual_session_id),
    )

    decision = await services.router.choose_route(
        prompt_request,
        classification,
    )
    render_route_explanation(decision)

    await services.persistence.persist_routing_decision(
        session_id=actual_session_id,
        request_id=request_id,
        decision=decision,
    )

    plan = services.planner.create_plan(
        request_id=request_id,
        session_id=actual_session_id,
        decision=decision,
        messages=[ProviderMessage(role="user", content=prompt)],
    )
    await services.persistence.persist_execution_plan(
        session_id=actual_session_id,
        request_id=request_id,
        plan_payload=plan.model_dump(),
    )

    if stream:
        await _stream_primary_route(services, plan)

    try:
        outcome = await services.lifecycle.execute(plan)
    except KeyboardInterrupt:
        services.lifecycle.cancel(request_id)
        await services.persistence.persist_snapshot(
            ContextSnapshot(
                session_id=actual_session_id,
                request_id=request_id,
                snapshot_type="interrupted",
                payload={"plan": plan.model_dump(), "hint": "Use resume command."},
            )
        )
        typer.echo(f"Execution interrupted. Resume with: smart-router resume {actual_session_id}")
        return

    render_execution_outcome(outcome)
    typer.echo(f"Session: {actual_session_id}")
    logger.info(
        "cli_run_completed",
        extra={
            "request_id": request_id,
            "session_id": actual_session_id,
            "active_provider": outcome.snapshot.active_provider,
            "selected_model": outcome.snapshot.active_model,
            "lifecycle_state": outcome.snapshot.state,
        },
    )

    # Snapshot final lifecycle checkpoint for resumability.
    await services.persistence.persist_snapshot(
        ContextSnapshot(
            session_id=actual_session_id,
            request_id=request_id,
            snapshot_type="final_outcome",
            payload={"state": outcome.snapshot.state, "plan": plan.model_dump()},
        )
    )


async def _stream_primary_route(services: AppServices, plan: ExecutionPlan) -> None:
    req = services.mapper.to_execution_request(
        plan,
        provider=plan.primary_provider,
        model=plan.primary_model,
    )
    try:
        async for event in services.orchestrator.stream_execute(req):
            render_stream_event(event)
    except Exception as exc:
        typer.echo(f"[stream] unavailable ({exc})")
