# SESSION CONTEXT

## Current assumptions

* OpenAI provider now exists as canonical provider implementation in `smart_router/providers/openai`.
* Config engine and provider registry integration path is functional via `OpenAIProvider.from_config_engine` and `register_openai_provider`.
* Future provider modules should mirror this contract and isolation pattern.

## Current blockers

* Automated test execution is currently blocked by missing `pytest` in `.venv`.

## Temporary reasoning

* Implemented provider-agnostic stream event normalization while keeping the existing `ProviderAdapter.stream()` signature.
* Kept all OpenAI-specific behavior inside adapter boundaries (no routing or CLI coupling).
