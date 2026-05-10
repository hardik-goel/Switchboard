"""Provider reliability and degradation analytics."""

from __future__ import annotations

from collections import defaultdict

from smart_router.core.telemetry.schemas import TelemetryEvent


class ProviderPerformanceTracker:
    """Compute provider success/failure rates and degradation trends."""

    def success_failure_rates(self, events: list[TelemetryEvent]) -> dict[str, dict[str, float]]:
        counts: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0, "total": 0})
        for event in events:
            if not event.provider:
                continue
            if event.event_type not in ("execution_completed", "execution_failed"):
                continue
            counts[event.provider]["total"] += 1
            if event.event_type == "execution_completed":
                counts[event.provider]["success"] += 1
            else:
                counts[event.provider]["failure"] += 1

        result: dict[str, dict[str, float]] = {}
        for provider, c in counts.items():
            total = max(1, c["total"])
            result[provider] = {
                "success_rate": c["success"] / total,
                "failure_rate": c["failure"] / total,
            }
        return result
