"""Repository scope inference heuristics."""

from __future__ import annotations

from smart_router.core.analyzer.schemas import FileMetadata, RepoMetadata
from smart_router.schemas.classification import RepoScope


class RepoScopeAnalyzer:
    """Infer likely repository scope from prompt + optional metadata."""

    def analyze(
        self,
        prompt: str,
        *,
        repo_metadata: RepoMetadata | None,
        file_metadata: FileMetadata | None,
    ) -> RepoScope:
        text = prompt.lower()

        if any(k in text for k in ("architecture", "redesign", "repo-wide", "across repo", "entire codebase")):
            return "architectural" if "architecture" in text or "redesign" in text else "repo_wide"

        if any(k in text for k in ("all files", "every file", "global", "project-wide", "migration")):
            return "repo_wide"

        changed_files = len(file_metadata.changed_files) if file_metadata else 0
        if changed_files >= 5:
            return "repo_wide"
        if changed_files >= 2:
            return "multi_file"

        if repo_metadata and repo_metadata.file_count and repo_metadata.file_count > 2000 and "refactor" in text:
            return "multi_file"

        if any(k in text for k in ("multiple files", "cross-file", "across modules", "module")):
            return "multi_file"

        return "single_file"
