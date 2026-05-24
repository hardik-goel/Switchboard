# Switchboard

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active%20development-orange)
![CLI](https://img.shields.io/badge/interface-CLI-informational)

Developer-first AI routing CLI for coding workflows.

Switchboard is a local CLI that analyzes prompts, selects a provider route, executes with retries/fallbacks, and stores telemetry/session state locally. It is designed for engineers who want explicit routing decisions and reproducible execution behavior.

## Current Release Scope

Implemented and working:

- CLI commands for run, explain, resume, providers, telemetry, sessions, config
- provider adapters: OpenAI and Anthropic
- deterministic prompt analysis + routing engine
- execution lifecycle with retry and fallback handling
- streaming output support
- local SQLite persistence:
  - `.smart_router/sessions.db`
  - `.smart_router/telemetry.db`

Planned (not in current release scope):

- Ollama provider
- Gemini provider
- sensitivity-aware cloud blocking policies
- project-level `.switchboard.yaml` overrides

## Why Use It

- route transparency: see why a provider/model path was selected
- resiliency: retries and fallback chain are built in
- observability: local telemetry and session history are persisted
- modularity: provider/router/policy layers are decoupled and testable

## Prerequisites

- Python 3.11+
- `pip`
- API key for at least one configured provider:
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`

## Quick Start

### 1. Clone and install

```bash
git clone <your-fork-or-this-repo-url>
cd Switchboard
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 2. Configure provider keys

```bash
export OPENAI_API_KEY="<your-openai-key>"
export ANTHROPIC_API_KEY="<your-anthropic-key>"
```

### 3. Verify CLI entrypoints

```bash
switchboard --help
smart-router --help
```

### 4. Validate config and provider health

```bash
switchboard config validate
switchboard providers health
```

### 5. Explain a route

```bash
switchboard explain "Write unit tests for auth middleware"
```

### 6. Execute

```bash
switchboard run "Refactor this function"
# alias
switchboard ask "Refactor this function"
```

## Commands

```bash
# Execution
switchboard run "<prompt>"
switchboard ask "<prompt>"
switchboard interactive
switchboard resume <session-id>

# Routing
switchboard routes explain "<prompt>"
switchboard explain "<prompt>"

# Health and config
switchboard providers health
switchboard config validate

# Telemetry and sessions
switchboard telemetry summary
switchboard sessions active
switchboard sessions show <session-id>
switchboard sessions history <session-id>
```

## Configuration

Default config file:

- `smart_router/configs/default.yaml`

Configuration controls include:

- enabled providers and models
- provider settings (`timeout_seconds`, `max_retries`)
- routing defaults (primary provider, fallback order)
- cost/latency preferences

## Testing

```bash
pip install -e '.[dev]'
python3 -m pytest -q
```

Minimal packaging smoke check:

```bash
python3 -m pytest -q tests/test_packaging_smoke.py
```

## Project Structure

- `smart_router/cli/` CLI entrypoint and command layer
- `smart_router/core/` analyzer, router, orchestrator, retries, sessions, telemetry
- `smart_router/providers/` provider adapters
- `smart_router/schemas/` shared typed contracts
- `smart_router/tests/` unit and integration tests

## Contributing

Contributions are welcome. Keep changes scoped, add tests, and preserve modular boundaries.

Basic flow:

1. Fork repo
2. Create branch
3. Implement + test
4. Open PR with behavior summary and test evidence

## License

MIT

## Connect & Support

- [![LinkedIn](https://img.shields.io/badge/LinkedIn-Hardik%20Goel-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/hardik-goel-a6334936/)
- [![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-HardikGoel-FFDD00?logo=buymeacoffee&logoColor=000000)](https://buymeacoffee.com/HardikGoel)
