"""Task type detection heuristics."""

from __future__ import annotations

from smart_router.schemas.classification import TaskType


class TaskTypeDetector:
    """Infer coarse task type from prompt semantics."""

    _PATTERNS: list[tuple[TaskType, tuple[str, ...]]] = [
        ("migration", ("migrate", "migration", "upgrade all", "across repo")),
        ("architecture", ("architecture", "redesign", "system design", "re-architect")),
        ("debugging", ("debug", "trace", "stack trace", "failing test", "why is")),
        ("refactor", ("refactor", "clean up", "simplify", "extract")),
        ("feature", ("add", "implement", "build", "create endpoint", "new feature")),
        ("bugfix", ("fix", "bug", "issue", "error", "broken")),
        ("documentation", ("docs", "documentation", "readme", "comment")),
        ("testing", ("test", "pytest", "unit test", "integration test")),
    ]

    def detect(self, prompt: str) -> TaskType:
        text = prompt.lower()
        for task_type, keywords in self._PATTERNS:
            if any(keyword in text for keyword in keywords):
                return task_type
        return "unknown"
