"""Execution analytics aggregation engine."""

from __future__ import annotations

from smart_router.core.analytics.health_metrics_aggregator import HealthMetricsAggregator
from smart_router.core.analytics.provider_performance_tracker import ProviderPerformanceTracker
from smart_router.core.metrics.collectors import CostTracker, LatencyTracker, MetricsCollector, RoutingDecisionTracker
from smart_router.core.telemetry.schemas import TelemetryEvent


class ExecutionAnalyticsEngine:
    """Aggregate execution insights from telemetry event streams."""

    def __init__(
        self,
        *,
        metrics_collector: MetricsCollector | None = None,
        performance_tracker: ProviderPerformanceTracker | None = None,
        cost_tracker: CostTracker | None = None,
        latency_tracker: LatencyTracker | None = None,
        routing_tracker: RoutingDecisionTracker | None = None,
        health_aggregator: HealthMetricsAggregator | None = None,
    ) -> None:
        self._metrics = metrics_collector or MetricsCollector()
        self._performance = performance_tracker or ProviderPerformanceTracker()
        self._cost = cost_tracker or CostTracker()
        self._latency = latency_tracker or LatencyTracker()
        self._routing = routing_tracker or RoutingDecisionTracker()
        self._health = health_aggregator or HealthMetricsAggregator(self._performance)

    def summarize(self, events: list[TelemetryEvent]) -> dict[str, object]:
        return {
            "event_counts": self._metrics.collect_counts(events),
            "average_latency": self._latency.average_latency(events),
            "provider_latency": self._latency.by_provider(events),
            "provider_performance": self._performance.success_failure_rates(events),
            "cost_by_provider_model": self._cost.by_provider_model(events),
            "route_frequency": self._routing.route_frequency(events),
            "fallback_frequency": self._routing.fallback_frequency(events),
            "routing_confidence_distribution": self._routing.confidence_distribution(events),
            "provider_health_scores": self._health.provider_health_scores(events),
            "degraded_providers": self._health.degraded_providers(events),
        }
