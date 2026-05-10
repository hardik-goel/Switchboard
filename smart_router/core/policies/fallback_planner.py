"""Fallback chain planning policy component."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    provider: str
    model: str
    score: float


class FallbackPlanner:
    """Build compatible fallback chains from ranked candidates."""

    def plan(self, *, selected: Candidate, ranked: list[Candidate], max_items: int = 3) -> list[str]:
        out: list[str] = []
        for item in ranked:
            if item.provider == selected.provider and item.model == selected.model:
                continue
            if item.score <= 0:
                continue
            out.append(f"{item.provider}:{item.model}")
            if len(out) >= max_items:
                break
        return out
