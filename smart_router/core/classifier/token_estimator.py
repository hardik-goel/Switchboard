"""Deterministic token estimation heuristics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenHeuristics:
    """Configurable token estimation parameters."""

    chars_per_token: float = 4.0
    base_output_tokens: int = 120
    output_multiplier: float = 0.6
    context_multiplier: float = 0.25


class TokenEstimator:
    """Estimate prompt and output tokens with deterministic heuristics."""

    def __init__(self, heuristics: TokenHeuristics | None = None) -> None:
        self._h = heuristics or TokenHeuristics()

    def estimate(self, prompt: str, *, complexity_score: float, repo_scope_weight: float) -> tuple[int, int, int]:
        base_input = max(1, int(len(prompt) / self._h.chars_per_token))
        context_expansion = max(0, int(base_input * self._h.context_multiplier * repo_scope_weight))
        estimated_input = base_input + context_expansion
        estimated_output = max(
            self._h.base_output_tokens,
            int(estimated_input * self._h.output_multiplier * (1.0 + complexity_score)),
        )
        return estimated_input, estimated_output, context_expansion
