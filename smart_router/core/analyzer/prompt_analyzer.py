"""Prompt analyzer composing deterministic classifier modules."""

from __future__ import annotations

import logging

from smart_router.core.analyzer.schemas import AnalyzerExecutionContext, FileMetadata, RepoMetadata
from smart_router.core.classifier.complexity_classifier import ComplexityClassifier
from smart_router.core.classifier.latency_sensitivity_analyzer import LatencySensitivityAnalyzer
from smart_router.core.classifier.repo_scope_analyzer import RepoScopeAnalyzer
from smart_router.core.classifier.task_type_detector import TaskTypeDetector
from smart_router.core.classifier.token_estimator import TokenEstimator
from smart_router.schemas.classification import PromptClassification

logger = logging.getLogger("smart_router.analyzer.prompt")


class PromptAnalyzer:
    """Produce structured execution intelligence from raw prompts."""

    def __init__(
        self,
        *,
        task_type_detector: TaskTypeDetector | None = None,
        repo_scope_analyzer: RepoScopeAnalyzer | None = None,
        complexity_classifier: ComplexityClassifier | None = None,
        token_estimator: TokenEstimator | None = None,
        latency_analyzer: LatencySensitivityAnalyzer | None = None,
    ) -> None:
        self._task_type_detector = task_type_detector or TaskTypeDetector()
        self._repo_scope_analyzer = repo_scope_analyzer or RepoScopeAnalyzer()
        self._complexity_classifier = complexity_classifier or ComplexityClassifier()
        self._token_estimator = token_estimator or TokenEstimator()
        self._latency_analyzer = latency_analyzer or LatencySensitivityAnalyzer()

    async def analyze(
        self,
        prompt: str,
        *,
        repo_metadata: RepoMetadata | None = None,
        file_metadata: FileMetadata | None = None,
        execution_context: AnalyzerExecutionContext | None = None,
    ) -> PromptClassification:
        """Analyze prompt deterministically into routing-ready classification."""
        task_type = self._task_type_detector.detect(prompt)
        repo_scope = self._repo_scope_analyzer.analyze(
            prompt,
            repo_metadata=repo_metadata,
            file_metadata=file_metadata,
        )
        repo_scope_weight = {
            "single_file": 0.25,
            "multi_file": 0.55,
            "repo_wide": 0.80,
            "architectural": 1.0,
        }[repo_scope]

        complexity_level, complexity_score, reasoning_depth = self._complexity_classifier.classify(
            prompt,
            task_type=task_type,
            repo_scope_weight=repo_scope_weight,
        )

        in_tokens, out_tokens, context_expansion = self._token_estimator.estimate(
            prompt,
            complexity_score=complexity_score,
            repo_scope_weight=repo_scope_weight,
        )

        latency_sensitivity = self._latency_analyzer.analyze(prompt)
        confidence = self._confidence_score(prompt, complexity_score, repo_scope_weight)
        capabilities = self._suggested_capabilities(task_type, complexity_level, repo_scope)
        risk = self._risk_level(complexity_level, repo_scope)

        result = PromptClassification(
            complexity_level=complexity_level,
            complexity_score=complexity_score,
            reasoning_depth=reasoning_depth,
            estimated_input_tokens=in_tokens,
            estimated_output_tokens=out_tokens,
            estimated_total_tokens=in_tokens + out_tokens,
            context_expansion_tokens=context_expansion,
            repo_scope=repo_scope,
            latency_sensitivity=latency_sensitivity,
            task_type=task_type,
            confidence_score=confidence,
            suggested_capabilities=capabilities,
            execution_risk_level=risk,
            latency_sensitive=(latency_sensitivity != "low"),
            repo_wide_operation=(repo_scope in ("repo_wide", "architectural")),
        )

        ctx = execution_context or AnalyzerExecutionContext()
        logger.info(
            "prompt_analyzed",
            extra={
                "request_id": ctx.request_id,
                "session_id": ctx.session_id,
                "complexity_level": result.complexity_level,
                "reasoning_depth": result.reasoning_depth,
                "estimated_tokens": result.estimated_total_tokens,
                "repo_scope": result.repo_scope,
                "analyzer_confidence": result.confidence_score,
            },
        )
        return result

    def _confidence_score(self, prompt: str, complexity_score: float, repo_scope_weight: float) -> float:
        # Confidence rises with explicit intent signals and bounded ambiguity.
        keyword_boost = 0.15 if any(k in prompt.lower() for k in ("fix", "refactor", "migrate", "architecture")) else 0.0
        length_factor = min(0.20, len(prompt) / 600)
        base = 0.45 + keyword_boost + length_factor + (0.10 * (1 - abs(0.5 - complexity_score)))
        penalty = 0.10 if repo_scope_weight == 1.0 and len(prompt) < 35 else 0.0
        return max(0.0, min(1.0, base - penalty))

    def _suggested_capabilities(self, task_type: str, complexity_level: str, repo_scope: str) -> list[str]:
        caps = ["code_generation", "code_editing"]
        if task_type in ("debugging", "bugfix"):
            caps.append("root_cause_analysis")
        if task_type in ("architecture", "migration"):
            caps.extend(["long_context_reasoning", "planning"])
        if repo_scope in ("repo_wide", "architectural"):
            caps.append("repo_search")
        if complexity_level == "high":
            caps.append("high_reliability_reasoning")
        return sorted(set(caps))

    def _risk_level(self, complexity_level: str, repo_scope: str) -> str:
        if complexity_level == "high" or repo_scope in ("repo_wide", "architectural"):
            return "high"
        if complexity_level == "medium" or repo_scope == "multi_file":
            return "medium"
        return "low"
