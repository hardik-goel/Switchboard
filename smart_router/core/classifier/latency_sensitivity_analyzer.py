"""Latency sensitivity inference heuristics."""

from __future__ import annotations

from smart_router.schemas.classification import LatencySensitivity


class LatencySensitivityAnalyzer:
    """Infer expected latency sensitivity from prompt language."""

    def analyze(self, prompt: str) -> LatencySensitivity:
        text = prompt.lower()
        if any(k in text for k in ("urgent", "asap", "quickly", "hotfix", "immediately")):
            return "high"
        if any(k in text for k in ("fast", "quick")):
            return "medium"
        return "low"
