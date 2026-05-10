# SESSION CONTEXT

## Current assumptions

* Runtime execution foundation is now present in `core/orchestrator`, `core/runtime`, and `core/streaming`.
* Orchestrator executes provider decisions from registry and does not include routing logic.
* Stream lifecycle is normalized into provider-agnostic events.

## Current blockers

* Automated test execution is currently blocked by missing `pytest` in `.venv`.

## Temporary reasoning

* Added cancellable runtime context and timeout-aware stream pipeline for future routing/session/telemetry integration.
* Preserved provider abstraction: orchestrator uses registry + provider interface only.
