# SESSION CONTEXT

## Current assumptions

* Session/state persistence is now implemented with pluggable store abstraction (`InMemory` + `SQLite`).
* Execution lifecycle/retry/fallback/orchestrator/telemetry expose persistence hooks without ownership inversion.
* Recovery coordinator can restore executable plans from persisted snapshots.

## Current blockers

* Automated test execution is currently blocked by missing `pytest` in `.venv`.

## Temporary reasoning

* Kept persistence passive and state-oriented: sessions observe lifecycle transitions and snapshots but do not own routing/retry logic.
* Preserved separation between telemetry and persistence while allowing telemetry-reference attachment via hooks.
