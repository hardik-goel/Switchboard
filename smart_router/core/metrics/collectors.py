"""Normalized metrics collection primitives."""

from __future__ import annotations

from collections import defaultdict

from smart_router.core.telemetry.schemas import TelemetryEvent


class MetricsCollector:
    """Collect normalized metrics from telemetry events."""

    def collect_counts(self, events: list[TelemetryEvent]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for event in events:
            counts[event.event_type] += 1
        return dict(counts)


class CostTracker:
    """Aggregate estimated cost metrics."""

    def by_provider_model(self, events: list[TelemetryEvent]) -> dict[str, float]:
        totals: dict[str, float] = defaultdict(float)
        for event in events:
            if event.cost_estimate is None or event.provider is None or event.model is None:
                continue
            key = f"{event.provider}:{event.model}"
            totals[key] += float(event.cost_estimate)
        return dict(totals)


class LatencyTracker:
    """Aggregate latency metrics."""

    def average_latency(self, events: list[TelemetryEvent]) -> float:
        values = [float(e.latency) for e in events if e.latency is not None]
        if not values:
            return 0.0
        return sum(values) / len(values)

    def by_provider(self, events: list[TelemetryEvent]) -> dict[str, float]:
        buckets: dict[str, list[float]] = defaultdict(list)
        for event in events:
            if event.provider and event.latency is not None:
                buckets[event.provider].append(float(event.latency))
        return {k: (sum(v) / len(v)) for k, v in buckets.items()}


class RoutingDecisionTracker:
    """Track routing quality and route frequencies."""

    def route_frequency(self, events: list[TelemetryEvent]) -> dict[str, int]:
        freq: dict[str, int] = defaultdict(int)
        for event in events:
            if event.event_type != "route_selected" or not event.provider or not event.model:
                continue
            freq[f"{event.provider}:{event.model}"] += 1
        return dict(freq)

    def fallback_frequency(self, events: list[TelemetryEvent]) -> int:
        return sum(1 for event in events if event.event_type == "fallback_triggered")

    def confidence_distribution(self, events: list[TelemetryEvent]) -> dict[str, int]:
        dist: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
        for event in events:
            if event.event_type != "route_selected":
                continue
            value = float(event.metadata.get("routing_confidence", 0.0))
            if value < 0.34:
                dist["low"] += 1
            elif value < 0.67:
                dist["medium"] += 1
            else:
                dist["high"] += 1
        return dist
