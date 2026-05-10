# SESSION CONTEXT

## Current assumptions

* Anthropic provider is now implemented and follows the same abstraction/runtime contract as OpenAI.
* Runtime orchestrator + stream manager remain provider-agnostic with both OpenAI and Anthropic adapters.
* Provider-specific semantics are isolated within each provider module.

## Current blockers

* Automated test execution is currently blocked by missing `pytest` in `.venv`.

## Temporary reasoning

* Anthropic stream output is normalized to the same provider-agnostic chunk format consumed by `StreamManager`.
* Added tool-use preparation hook surface inside Anthropic adapter without leaking semantics into core runtime modules.
