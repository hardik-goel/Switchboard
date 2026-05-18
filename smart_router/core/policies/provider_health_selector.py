"""Provider health scoring policy component."""

from __future__ import annotations


class ProviderHealthSelector:
    """Apply provider health metadata as a deterministic score factor."""

    def score(self, provider: str, health_scores: dict[str, float] | None) -> float:
        if not health_scores:
            return 1.0
        return max(0.0, min(1.0, health_scores.get(provider, 1.0)))
