# ARCHITECTURE.md

# Smart AI Routing CLI — System Architecture

## Overview

This project is a production-grade local AI routing/orchestration CLI utility for coding workflows.

The system intelligently routes coding prompts/tasks between multiple AI providers and models based on:

* complexity
* latency sensitivity
* reasoning depth
* token requirements
* repository scale
* cost optimization
* provider availability
* fallback policies

Supported providers:

* OpenAI
* Anthropic
* Gemini
* Ollama/local models
* future providers

The architecture is:

* modular
* async-first
* config-driven
* provider-agnostic
* extensible
* AI-assisted-development friendly

---

# Core Principles

## 1. Strict Modularity

Every module:

* independently buildable
* independently testable
* independently replaceable

No module should depend on internal implementation details of another module.

Communication must occur only through explicit contracts/interfaces.

---

## 2. Provider Abstraction

All AI providers expose a unified interface.

The routing engine must never contain provider-specific logic.

Provider implementations remain isolated.

---

## 3. Config-Driven Design

Models, routing policies, pricing, capabilities, and fallback behavior must live in configuration files.

Avoid hardcoded model assumptions.

---

## 4. Async-First Architecture

All provider calls, streaming, telemetry, retries, and orchestration are asynchronous.

Avoid blocking operations.

---

## 5. AI-Friendly Development

Architecture is intentionally optimized for:

* Claude Code
* Codex
* AI-assisted incremental implementation

The system must support:

* resumability
* isolated module implementation
* context-window-safe development

---

# High-Level System Flow

User Prompt
↓
CLI Layer
↓
Session Manager
↓
Prompt Analyzer
↓
Routing Engine
↓
Provider Orchestrator
↓
Selected Provider
↓
Streaming Response
↓
Telemetry + Persistence

---

# Folder Structure

smart-router/
│
├── .ai/
│
├── cli/
│   ├── main.py
│   ├── commands/
│   └── ui/
│
├── core/
│   ├── router/
│   ├── classifier/
│   ├── orchestrator/
│   ├── streaming/
│   ├── retries/
│   ├── sessions/
│   ├── telemetry/
│   ├── config/
│   └── context/
│
├── providers/
│   ├── base/
│   ├── openai/
│   ├── anthropic/
│   ├── gemini/
│   └── ollama/
│
├── schemas/
│
├── configs/
│
├── tests/
│
├── scripts/
│
└── docs/

---

# Module Responsibilities

---

## CLI Layer

Responsibilities:

* terminal UX
* command parsing
* argument validation
* rendering streaming output
* invoking orchestration flow

Rules:

* NO business logic
* NO provider-specific logic
* NO routing decisions

---

## Session Manager

Responsibilities:

* maintain conversational continuity
* store/recover active sessions
* persist context safely
* support interrupted task recovery

Storage:

* SQLite
* optional JSON snapshots

---

## Prompt Analyzer

Responsibilities:

* estimate complexity
* estimate token usage
* classify task type
* detect repo-wide operations
* determine reasoning depth
* detect latency sensitivity

Output:
Structured classification object.

---

## Routing Engine

Responsibilities:

* choose optimal model/provider
* apply routing policies
* apply pricing constraints
* apply fallback logic
* apply user preferences

Inputs:

* classification output
* model registry
* telemetry
* config rules

Outputs:

* routing decision object

Rules:

* deterministic
* explainable
* observable

---

## Provider Orchestrator

Responsibilities:

* invoke provider adapters
* manage retries
* manage fallback chains
* normalize provider responses
* manage streaming

---

## Provider Adapters

Responsibilities:

* API communication
* auth handling
* request formatting
* response normalization
* streaming normalization

Each provider must implement:

* generate()
* stream()
* validate_config()
* health_check()

Provider adapters must not leak provider-specific structures outside.

---

## Telemetry Engine

Responsibilities:

* latency tracking
* token accounting
* provider performance
* routing decisions
* failures/retries
* cost analytics

Storage:
SQLite initially.

---

## Config Engine

Responsibilities:

* load YAML configs
* validate schemas
* merge overrides
* environment handling
* runtime config reloads

---

# Core Interfaces

---

## Provider Interface

All providers implement:

```python
class BaseProvider:
    async def generate(self, request): ...
    async def stream(self, request): ...
    async def validate_config(self): ...
    async def health_check(self): ...
```

---

## Router Interface

```python
class Router:
    async def route(self, analyzed_prompt): ...
```

---

## Analyzer Interface

```python
class PromptAnalyzer:
    async def analyze(self, prompt, context): ...
```

---

# Config System

Configuration files live under:

configs/

Examples:

* models.yaml
* routing.yaml
* pricing.yaml
* providers.yaml

---

# Example Model Config

```yaml
models:
  claude-haiku:
    provider: anthropic
    reasoning: low
    speed: very_fast
    context_window: 200000
    pricing:
      input: 0.25
      output: 1.25

  gpt-5.5:
    provider: openai
    reasoning: very_high
    speed: medium
```

---

# Routing Logic

Routing decisions may consider:

* complexity score
* token estimate
* repo size
* latency requirements
* pricing budget
* provider health
* historical success rates
* fallback chains

Routing rules remain config-driven where possible.

---

# Streaming Architecture

Streaming must:

* normalize provider token streams
* support cancellation
* support retries
* support partial persistence

CLI consumes normalized stream events only.

---

# Retry/Fallback Strategy

Failures categorized:

* transient
* auth
* rate limit
* provider unavailable
* timeout
* malformed response

Retry engine responsibilities:

* retry policies
* fallback model switching
* exponential backoff

---

# Session Persistence

Sessions must support:

* resumability
* interruption recovery
* provider switching
* streaming continuation

Session state stored independently from provider implementations.

---

# Telemetry Schema

Tracked metrics:

* prompt id
* provider
* model
* latency
* token counts
* cost estimate
* retries
* fallback usage
* success/failure
* route reasoning

---

# Testing Strategy

Required:

* unit tests
* contract tests
* provider mock tests
* integration tests
* routing logic tests

Avoid:

* tightly coupled tests
* provider-live-only tests

---

# Error Handling Principles

* explicit exceptions
* structured logging
* observable failures
* no silent retries
* no swallowed errors

---

# Logging Principles

Use structured logs only.

Required fields:

* module
* operation
* provider
* latency
* session_id
* request_id

---

# Dependency Rules

Allowed:

* schemas shared globally
* interfaces shared globally

Disallowed:

* provider-to-provider imports
* CLI-to-provider direct imports
* router-to-provider concrete coupling

---

# Future Extensibility

Architecture must support:

* new providers
* local models
* multi-model parallel inference
* self-optimizing routing
* agent workflows
* RAG integration
* plugin ecosystem

without major rewrites.

---

# Recommended Implementation Order

1. schemas
2. config engine
3. provider base contracts
4. OpenAI provider
5. Anthropic provider
6. routing engine
7. prompt analyzer
8. telemetry
9. sessions
10. streaming
11. retries/fallbacks
12. CLI
13. integration
14. optimization

---

# Non-Goals (Current Scope)

Not currently implementing:

* GUI
* distributed orchestration
* cloud sync
* autonomous agents
* multi-user support

These may be added later.

---

# Architectural Constraints

DO NOT:

* create monolith modules
* hardcode providers
* tightly couple modules
* bypass interfaces
* skip typing/contracts
* place business logic in CLI

ALWAYS:

* preserve modularity
* preserve async flow
* preserve config-driven behavior
* preserve provider abstraction
* preserve resumability
