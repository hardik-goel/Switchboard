# PROJECT VISION

## Goal

Build a production-grade local AI routing/orchestration CLI utility for coding workflows.

The system intelligently routes prompts/tasks between:

* OpenAI GPT family
* Claude Haiku/Sonnet/Opus
* Gemini
* Ollama/local models
* future providers

based on:

* complexity
* reasoning depth
* token estimation
* repository scale
* latency requirements
* cost optimization
* user preferences
* fallback strategies

The utility must:

* run locally in terminal
* support streaming
* support resumability
* support telemetry
* support retries/fallbacks
* support pluggable providers
* remain config-driven
* support modular development
* support AI-assisted/vibe-coded implementation

Primary UX:
CLI-first developer workflow.

Core philosophy:

* strict modularity
* explicit contracts
* minimal coupling
* production-grade maintainability
* future-safe extensibility
