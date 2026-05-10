# SESSION CONTEXT

## Current assumptions

* CLI now exposes end-to-end flow and remains orchestration-only (analyzer/router/execution primitives).
* Session persistence + telemetry hooks are integrated into CLI execution paths.
* Route explanation, telemetry summary, provider health, resume, and session inspection commands are available.

## Current blockers

* Automated test execution is currently blocked by missing `pytest` in `.venv`.
* Runtime import checks are blocked by missing core dependencies in `.venv`.

## Temporary reasoning

* Kept CLI thin and delegated core logic to existing modules.
* Added hook-based UX visibility for streaming and lifecycle outcomes without moving retry/routing/provider logic into CLI.
