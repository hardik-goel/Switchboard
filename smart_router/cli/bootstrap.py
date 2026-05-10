"""CLI service bootstrap and dependency wiring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from smart_router.core.analyzer import PromptAnalyzer
from smart_router.core.config import ConfigEngine
from smart_router.core.execution import ExecutionLifecycleManager, ExecutionPlanner, RouteExecutionMapper
from smart_router.core.orchestrator import ProviderOrchestrator
from smart_router.core.persistence import SQLiteSessionStore, SessionPersistenceEngine
from smart_router.core.registry import ProviderRegistry
from smart_router.core.router import RoutingEngine
from smart_router.core.sessions import RecoveryCoordinator, SessionLifecycleManager, SessionManager
from smart_router.core.telemetry import SQLiteTelemetryStorage, TelemetryManager
from smart_router.providers.anthropic import register_anthropic_provider
from smart_router.providers.openai import register_openai_provider


@dataclass
class AppServices:
    """Container for CLI-layer service composition."""

    config_engine: ConfigEngine
    analyzer: PromptAnalyzer
    router: RoutingEngine
    orchestrator: ProviderOrchestrator
    planner: ExecutionPlanner
    mapper: RouteExecutionMapper
    lifecycle: ExecutionLifecycleManager
    telemetry: TelemetryManager
    session_manager: SessionManager
    session_lifecycle: SessionLifecycleManager
    recovery: RecoveryCoordinator
    persistence: SessionPersistenceEngine
    registry: ProviderRegistry


def build_services(config_path: Path | None = None, data_dir: Path | None = None) -> AppServices:
    """Wire all runtime services used by CLI commands."""
    base_dir = data_dir or Path(".smart_router")
    base_dir.mkdir(parents=True, exist_ok=True)

    cfg_path = config_path or Path("smart_router/configs/default.yaml")
    config_engine = ConfigEngine(cfg_path)
    app_config = config_engine.load()

    persistence = SessionPersistenceEngine(SQLiteSessionStore(base_dir / "sessions.db"))
    telemetry = TelemetryManager(
        storage=SQLiteTelemetryStorage(base_dir / "telemetry.db"),
        session_hook=persistence.hook(),
    )

    registry = ProviderRegistry()
    if "openai" in app_config.providers:
        register_openai_provider(registry, config_engine)
    if "anthropic" in app_config.providers:
        register_anthropic_provider(registry, config_engine)

    orchestrator = ProviderOrchestrator(
        registry,
        telemetry_hook=telemetry.hook(),
        persistence_hook=persistence.hook(),
    )

    router = RoutingEngine(
        app_config,
        telemetry_hook=telemetry.hook(),
    )

    lifecycle = ExecutionLifecycleManager(
        orchestrator,
        telemetry_hook=telemetry.hook(),
        persistence_hook=persistence.hook(),
    )

    return AppServices(
        config_engine=config_engine,
        analyzer=PromptAnalyzer(),
        router=router,
        orchestrator=orchestrator,
        planner=ExecutionPlanner(),
        mapper=RouteExecutionMapper(),
        lifecycle=lifecycle,
        telemetry=telemetry,
        session_manager=SessionManager(persistence),
        session_lifecycle=SessionLifecycleManager(persistence),
        recovery=RecoveryCoordinator(persistence),
        persistence=persistence,
        registry=registry,
    )
