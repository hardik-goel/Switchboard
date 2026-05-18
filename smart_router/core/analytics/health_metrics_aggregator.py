"""Provider health metrics aggregation."""

from __future__ import annotations

from smart_router.core.analytics.provider_performance_tracker import ProviderPerformanceTracker
from smart_router.core.telemetry.schemas import TelemetryEvent


class HealthMetricsAggregator:
    """Compute health summaries and degraded-provider hooks."""

    def __init__(self, performance_tracker: ProviderPerformanceTracker | None = None) -> None:
        self._performance = performance_tracker or ProviderPerformanceTracker()

    def provider_health_scores(self, events: list[TelemetryEvent]) -> dict[str, float]:
        rates = self._performance.success_failure_rates(events)
        return {provider: max(0.0, min(1.0, stats["success_rate"] - (0.5 * stats["failure_rate"]))) for provider, stats in rates.items()}

    def degraded_providers(self, events: list[TelemetryEvent], *, threshold: float = 0.5) -> list[str]:
        scores = self.provider_health_scores(events)
        return [provider for provider, score in scores.items() if score < threshold]
