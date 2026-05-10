# DECISIONS LOG

## Architectural Decisions

### 2026-05-10: Use package root `smart_router/` for all modules

Decision:
Initialize a single Python package (`smart_router`) with subpackages aligned to architecture domains (`cli`, `core`, `providers`, `schemas`, `tests`).

Reason:
Preserves strict modularity and keeps imports explicit and testable from the start.

Impact:
Future modules can be added without restructuring paths or introducing hidden coupling.

### 2026-05-10: Define contracts as runtime-checkable protocols

Decision:
Define core interfaces in `core/interfaces` using `typing.Protocol` with async method signatures.

Reason:
Enforces provider-agnostic design and supports independent adapter implementations.

Impact:
Routing/orchestration modules can depend on contracts only, not provider internals.

### 2026-05-10: Centralize config loading behind ConfigEngine

Decision:
Use a single typed `ConfigEngine` (`core/config/engine.py`) to load and validate YAML into `AppConfig`.

Reason:
Keeps config-driven design explicit and prevents ad-hoc YAML parsing across modules.

Impact:
Routing, providers, and orchestration will consume normalized typed config only.

### 2026-05-10: Introduce ProviderRegistry with factory registration

Decision:
Provider adapter instantiation is routed through a `ProviderRegistry` that stores named factories.

Reason:
Avoids hidden dependencies and allows pluggable providers/future extensions without changing orchestration code.

Impact:
Provider orchestration can resolve adapters by provider name deterministically.

### 2026-05-10: OpenAI provider is canonical adapter pattern

Decision:
Implement `smart_router/providers/openai` as the reference provider with strict isolation, typed config validation, typed exceptions, normalized streaming events, and retry-safe request handling.

Reason:
Future providers need a production-grade template that enforces abstraction boundaries and consistent behavior.

Impact:
Anthropic/Gemini/Ollama adapters can mirror the same architecture with minimal risk of interface drift.

### 2026-05-10: Runtime orchestration is split across orchestrator/runtime/streaming modules

Decision:
Implement runtime execution as three focused layers: `RuntimeExecutionContext` for execution state, `ProviderOrchestrator` for lifecycle + provider invocation, and `StreamManager` for provider-agnostic stream normalization.

Reason:
Keeps responsibilities isolated, avoids routing leakage, and enables future telemetry/session/retry integration without redesign.

Impact:
Execution pipeline is now a stable foundation that can consume routing decisions later while remaining provider-agnostic.
