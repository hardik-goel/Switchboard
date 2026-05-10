from __future__ import annotations

import pytest

from smart_router.core.analyzer import AnalyzerExecutionContext, FileMetadata, PromptAnalyzer, RepoMetadata
from smart_router.core.classifier import TokenEstimator


@pytest.mark.asyncio
async def test_trivial_task_classification_low() -> None:
    analyzer = PromptAnalyzer()
    result = await analyzer.analyze("fix typo in README")
    assert result.complexity_level == "low"
    assert result.task_type in ("bugfix", "documentation")
    assert result.repo_scope == "single_file"


@pytest.mark.asyncio
async def test_debugging_classification() -> None:
    analyzer = PromptAnalyzer()
    result = await analyzer.analyze("debug failing test and trace auth issue")
    assert result.task_type == "debugging"
    assert result.reasoning_depth in ("medium", "high")


@pytest.mark.asyncio
async def test_refactor_multi_file_scope() -> None:
    analyzer = PromptAnalyzer()
    result = await analyzer.analyze(
        "refactor payment workflow across modules",
        file_metadata=FileMetadata(changed_files=["a.py", "b.py", "c.py"]),
    )
    assert result.repo_scope in ("multi_file", "repo_wide")
    assert result.complexity_level in ("medium", "high")


@pytest.mark.asyncio
async def test_architecture_redesign_high() -> None:
    analyzer = PromptAnalyzer()
    result = await analyzer.analyze("architecture redesign for auth and concurrency")
    assert result.complexity_level == "high"
    assert result.execution_risk_level == "high"
    assert result.repo_scope == "architectural"


@pytest.mark.asyncio
async def test_repo_migration_repo_wide() -> None:
    analyzer = PromptAnalyzer()
    result = await analyzer.analyze("migrate repo-wide API calls from v1 to v2 across all files")
    assert result.task_type == "migration"
    assert result.repo_scope in ("repo_wide", "architectural")


@pytest.mark.asyncio
async def test_latency_inference() -> None:
    analyzer = PromptAnalyzer()
    result = await analyzer.analyze("urgent hotfix: fix broken endpoint quickly")
    assert result.latency_sensitivity in ("high", "medium")
    assert result.latency_sensitive is True


@pytest.mark.asyncio
async def test_confidence_scoring_bounds() -> None:
    analyzer = PromptAnalyzer()
    result = await analyzer.analyze("refactor service")
    assert 0.0 <= result.confidence_score <= 1.0


def test_token_estimation_contract() -> None:
    estimator = TokenEstimator()
    in_tokens, out_tokens, expansion = estimator.estimate(
        "refactor logic across repository modules",
        complexity_score=0.7,
        repo_scope_weight=0.8,
    )
    assert in_tokens > 0
    assert out_tokens >= 120
    assert expansion >= 0


@pytest.mark.asyncio
async def test_analyzer_contract_fields_present() -> None:
    analyzer = PromptAnalyzer()
    result = await analyzer.analyze(
        "add endpoint and tests",
        repo_metadata=RepoMetadata(file_count=450),
        execution_context=AnalyzerExecutionContext(request_id="r1", session_id="s1"),
    )
    assert result.complexity_level in ("low", "medium", "high")
    assert result.reasoning_depth in ("low", "medium", "high")
    assert result.estimated_total_tokens == result.estimated_input_tokens + result.estimated_output_tokens
    assert isinstance(result.suggested_capabilities, list)
