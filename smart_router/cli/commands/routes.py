"""Routes explanation commands."""

from __future__ import annotations

from smart_router.cli.bootstrap import AppServices
from smart_router.cli.rendering.console import render_route_explanation
from smart_router.core.analyzer import AnalyzerExecutionContext
from smart_router.schemas.prompt import PromptRequest


async def explain_route(services: AppServices, prompt: str) -> None:
    classification = await services.analyzer.analyze(prompt, execution_context=AnalyzerExecutionContext())
    decision = await services.router.choose_route(PromptRequest(prompt=prompt), classification)
    render_route_explanation(decision)
