# SESSION CONTEXT

## Current assumptions

* Routing engine now consumes only `PromptClassification` + config/runtime metadata and emits structured `RoutingDecision`.
* Routing policies are deterministic, config-driven, and provider-SDK agnostic.
* Analyzer, router, and orchestrator remain separated by explicit schemas/contracts.

## Current blockers

* Automated test execution is currently blocked by missing `pytest` in `.venv`.

## Temporary reasoning

* Implemented policy layer composition (`capability`, `cost`, `latency`, `health`) for explainable deterministic scoring.
* Added fallback planning from ranked candidates without hardcoding provider names in routing logic.
