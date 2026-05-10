# SESSION CONTEXT

## Current assumptions

* Prompt analyzer + deterministic classifier stack is now implemented in `core/analyzer` and `core/classifier`.
* Analyzer outputs are provider-agnostic and routing-ready via structured `PromptClassification` schema.
* Runtime/orchestration modules remain decoupled from analysis logic.

## Current blockers

* Automated test execution is currently blocked by missing `pytest` in `.venv`.

## Temporary reasoning

* Kept heuristics deterministic and modular for future ML-pluggable classifier replacement.
* Preserved strict separation: analyzer performs semantic intelligence only, with no routing/provider/pricing logic.
