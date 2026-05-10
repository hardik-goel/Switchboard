"""Prompt complexity and reasoning-depth heuristics."""

from __future__ import annotations

from smart_router.schemas.classification import ComplexityLevel, ReasoningDepth, TaskType


class ComplexityClassifier:
    """Deterministically score prompt complexity without external ML."""

    def classify(self, prompt: str, *, task_type: TaskType, repo_scope_weight: float) -> tuple[ComplexityLevel, float, ReasoningDepth]:
        text = prompt.lower()
        score = 0.15

        high_signals = ("architecture", "concurrency", "auth", "migration", "distributed", "thread")
        medium_signals = ("refactor", "endpoint", "logic", "integration", "workflow")
        low_signals = ("rename", "typo", "format", "lint", "comment")

        score += 0.30 if any(k in text for k in high_signals) else 0.0
        score += 0.18 if any(k in text for k in medium_signals) else 0.0
        score -= 0.12 if any(k in text for k in low_signals) else 0.0

        if task_type in ("architecture", "migration"):
            score += 0.20
        elif task_type in ("refactor", "feature", "debugging"):
            score += 0.10

        score += 0.15 * repo_scope_weight
        score = max(0.0, min(1.0, score))

        if score < 0.33:
            return "low", score, "low"
        if score < 0.67:
            return "medium", score, "medium"
        return "high", score, "high"
