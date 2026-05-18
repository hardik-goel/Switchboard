"""Telemetry CLI commands."""

from __future__ import annotations

from smart_router.cli.bootstrap import AppServices
from smart_router.cli.rendering.console import render_telemetry_summary


async def telemetry_summary(services: AppServices) -> None:
    summary = await services.telemetry.analytics_summary()
    render_telemetry_summary(summary)
