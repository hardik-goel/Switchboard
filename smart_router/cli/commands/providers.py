"""Provider health CLI commands."""

from __future__ import annotations

from smart_router.cli.bootstrap import AppServices
from smart_router.cli.rendering.console import render_provider_health


async def providers_health(services: AppServices) -> None:
    data: dict[str, object] = {}
    for provider_name in services.config_engine.config.providers:
        try:
            provider = services.registry.create(provider_name)
            healthy = await provider.health_check()
            data[provider_name] = {"reachable": bool(healthy)}
        except Exception as exc:
            data[provider_name] = {"reachable": False, "error": str(exc)}
    render_provider_health(data)
